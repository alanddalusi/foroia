from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict,Field,model_validator
from datetime import datetime,timedelta
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.limits import get_redis
from redis.exceptions import RedisError
from app.models import AuditLog, ResearchControl, ResearchRun, EditorialCandidate,EditorialExecution,EditorialLaneRun,GenerationUsage,Article,NewsScan,utcnow
from app.research.recovery import PENDING,disposition
from app.modules.articles.editorial import require_editor
from app.research.config import MADRID, settings
from app.research.sources import FEEDS

router = APIRouter(prefix='/editorial/research', tags=['editorial'], dependencies=[Depends(require_editor)])
DB = Annotated[AsyncSession, Depends(get_db)]

def execution_view(row):
    return dict(id=row.id,state=row.state,reason=row.reason,candidate_id=row.candidate_id,article_id=row.article_id,
        stage=row.report.get('current_stage'),max_usd=f'{row.max_reserved_microusd/1000000:.6f}',
        reserved_usd=f'{row.reserved_microusd/1000000:.6f}',max_microusd=row.max_reserved_microusd,
        quote_digest=row.prepared.get('quote_digest'),expires_at=row.expires_at,created_at=row.created_at,
        preflight=row.report.get('preflight'),failure=row.report.get('generation_failure') if row.state in {'failed','uncertain','expired'} else None,
        review=row.report.get('review'),verification=row.report.get('verification'),
        backlog_authorization_id=row.prepared.get('backlog_authorization_id'),
        stages=[dict(stage=v.get('stage'),state=v.get('state'),reason=v.get('reason')) for v in row.report.get('stage_checkpoints',{}).values()])

class ExecutionWrite(BaseModel):
    model_config=ConfigDict(extra='forbid')
    mode:str=Field(pattern=r'^(auto|resume|correction)$')
    candidate_id:int|None=Field(default=None,gt=0)
    request_key:str=Field(pattern=r'^[a-zA-Z0-9-]{16,64}$')
    backlog_candidate_ids:list[int]|None=Field(default=None,min_length=1,max_length=12)
    backlog_authorization_id:int|None=Field(default=None,gt=0)

class ExecutionConfirm(BaseModel):
    model_config=ConfigDict(extra='forbid')
    quote_digest:str=Field(pattern=r'^[a-f0-9]{64}$')
    max_microusd:int=Field(ge=0,le=150000)

@router.post('/executions')
async def request_execution(payload:ExecutionWrite,db:DB,actor:Annotated[str,Depends(require_editor)]):
    from app.research.executions import ACTIVE
    from app.core.limits import limit
    await limit('research-prepare',actor,10,300)
    control=await db.scalar(select(ResearchControl).where(ResearchControl.id==1).with_for_update())
    if not control:raise HTTPException(503,'Control no configurado')
    prior=await db.scalar(select(EditorialExecution).where(EditorialExecution.request_key==payload.request_key))
    if prior:
        if prior.mode!=payload.mode or (payload.candidate_id and prior.candidate_id!=payload.candidate_id):raise HTTPException(409,'Clave utilizada para otra solicitud')
        return execution_view(prior)
    from app.research.documents import aware
    active=(await db.scalars(select(EditorialExecution).where(EditorialExecution.state.in_(ACTIVE)))).all()
    for row in active:
        if row.state=='awaiting_approval' and aware(row.expires_at)<utcnow():row.state='expired';row.reason='quote_expired'
        else:raise HTTPException(409,'Ya existe una ejecución pendiente')
    if payload.backlog_candidate_ids and payload.backlog_authorization_id:raise HTTPException(422,'Selecciona una autorización')
    permit=payload.backlog_authorization_id
    if payload.backlog_candidate_ids:
        ids=payload.backlog_candidate_ids
        if len(set(ids))!=len(ids) or any(i<=0 for i in ids) or payload.candidate_id not in ids:
            raise HTTPException(422,'Lote inválido')
        candidates=(await db.scalars(select(EditorialCandidate).where(EditorialCandidate.id.in_(ids)))).all()
        if len(candidates)!=len(ids) or any(c.engine!='evergreen' or c.target_article_id for c in candidates):
            raise HTTPException(422,'El lote solo admite candidatos prácticos existentes')
        audit=AuditLog(actor=actor,action='editorial_backlog_authorized',entity_type='research',entity_id=1,
            details={'editorial_date':str(utcnow().astimezone(MADRID).date()),'candidate_ids':ids,
                     'maximum_publications':len(ids),'budgets_unchanged':True})
        db.add(audit);await db.flush();permit=audit.id
    if permit:
        audit=await db.get(AuditLog,permit)
        scope=audit.details if audit and audit.action=='editorial_backlog_authorized' else {}
        if scope.get('editorial_date')!=str(utcnow().astimezone(MADRID).date()) or payload.candidate_id not in scope.get('candidate_ids',[]):
            raise HTTPException(409,'Autorización caducada o ajena al candidato')
    row=EditorialExecution(mode=payload.mode,candidate_id=payload.candidate_id,request_key=payload.request_key,
        prepared={'backlog_authorization_id':permit} if permit else {})
    db.add(row);await db.flush()
    db.add(AuditLog(actor=actor,action='research_execution_prepare',entity_type='research',entity_id=row.id,details={'mode':row.mode}))
    await db.commit();return execution_view(row)

@router.post('/executions/{execution_id}/confirm')
async def confirm_execution(execution_id:int,payload:ExecutionConfirm,db:DB,actor:Annotated[str,Depends(require_editor)]):
    from app.research.executions import allowance,prices
    from app.research.documents import aware
    control=await db.scalar(select(ResearchControl).where(ResearchControl.id==1).with_for_update())
    row=await db.scalar(select(EditorialExecution).where(EditorialExecution.id==execution_id).with_for_update())
    if not row:raise HTTPException(404,'Ejecución no encontrada')
    if payload.quote_digest!=row.prepared.get('quote_digest') or payload.max_microusd!=row.max_reserved_microusd:raise HTTPException(409,'El presupuesto no coincide')
    if row.state in {'queued','running','completed'}:return execution_view(row)
    config=settings();day=utcnow().astimezone(MADRID).date()
    if row.state!='awaiting_approval' or aware(row.expires_at)<utcnow() or row.prepared.get('day')!=str(day):raise HTTPException(409,'Presupuesto caducado')
    if prices(config)!=row.prepared['prices'] or row.max_reserved_microusd>await allowance(db,config,day):raise HTTPException(409,'Presupuesto disponible cambiado')
    if not control or not control.enabled:raise HTTPException(409,'Reanuda la investigación antes de confirmar')
    row.state='queued'
    db.add(AuditLog(actor=actor,action='research_execution_confirm',entity_type='research',entity_id=row.id,details={'maximum_microusd':row.max_reserved_microusd}))
    await db.commit();return execution_view(row)

@router.post('/executions/{execution_id}/cancel')
async def cancel_execution(execution_id:int,db:DB,actor:Annotated[str,Depends(require_editor)]):
    await db.scalar(select(ResearchControl).where(ResearchControl.id==1).with_for_update())
    row=await db.scalar(select(EditorialExecution).where(EditorialExecution.id==execution_id).with_for_update())
    if not row:raise HTTPException(404,'Ejecución no encontrada')
    if row.state not in {'awaiting_approval','queued'}:raise HTTPException(409,'No se puede cancelar en esta etapa')
    row.state='failed';row.reason='cancelled';row.finished_at=utcnow()
    db.add(AuditLog(actor=actor,action='research_execution_cancel',entity_type='research',entity_id=row.id,details={}))
    await db.commit();return execution_view(row)


class ControlWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool
    rapid_enabled:bool|None=None


def report_view(report):
    data=dict(report)
    if report.get('editorial_version')==2:
        discovery=report.get('news_discovery',{})
        selection=discovery.get('selection')
        data['selection']=selection if isinstance(selection,dict) else None
        safe_discovery={k:v for k,v in discovery.items() if k not in {'selection','document_snapshots'}}
        if 'web' in safe_discovery:
            safe_discovery['web']={k:v for k,v in safe_discovery['web'].items() if k not in {'raw','usage'}}
        data['news_discovery']=safe_discovery
        data['web_discovery']=safe_discovery
        if not data.get('web_research') and discovery.get('web'):
            data['web_research']=discovery['web']
        data['news_statistics']=discovery.get('statistics',{})
        data['fetch_errors']=[*discovery.get('statistics',{}).get('fetch_errors',[]),*report.get('fetch_errors',[])]
    for slot in ('web_research','alternative_web_research'):
        if slot in data:data[slot]={k:v for k,v in data[slot].items() if k not in {'raw','usage'}}
    def public_summary(value):
        # Recovery histories can nest complete previous reports. Keep model
        # responses and document bodies private at every nesting level.
        if isinstance(value,dict):return {k:public_summary(v) for k,v in value.items() if k not in {'raw','usage','document_snapshots'}}
        if isinstance(value,list):return [public_summary(v) for v in value]
        return value
    return public_summary(data)


@router.get('')
async def overview(db: DB):
    config = settings()
    control = await db.get(ResearchControl, 1)
    rows = (await db.scalars(select(ResearchRun).order_by(ResearchRun.editorial_date.desc()).limit(14))).all()
    month = utcnow().astimezone(MADRID).date().replace(day=1)
    reserved = await db.scalar(select(func.coalesce(func.sum(ResearchRun.reserved_microusd), 0)).where(ResearchRun.editorial_date >= month))
    try:
        worker_alive = bool(await get_redis().get('foroia:research:heartbeat'))
        rapid_alive=bool(await get_redis().get('foroia:research:news-heartbeat'))
        raw_health=await get_redis().get('foroia:editorial:health')
    except RedisError:
        worker_alive = False
        rapid_alive=False
        raw_health=None
    import json
    try:health=json.loads(raw_health) if raw_health and len(raw_health)<50000 else None
    except (ValueError,TypeError):health=None
    day_reserved=0
    now=utcnow().astimezone(MADRID)
    today=next((r for r in rows if r.editorial_date==now.date()),None)
    day_reserved=today.reserved_microusd if today else 0
    start=datetime.combine(now.date(),datetime.min.time(),tzinfo=MADRID)
    published_today=await db.scalar(select(EditorialCandidate.id).join(Article,Article.id==EditorialCandidate.article_id).where(Article.status=='published',Article.published_at>=start).limit(1))
    budget_pending=bool(today and today.report.get('budget_bucket') and not today.report.get('nightly_started'))
    next_day=now.date()+timedelta(days=1) if published_today or (today and not budget_pending) or (not budget_pending and now.time()>=config.at) else now.date()
    upcoming=datetime.combine(next_day,config.at,tzinfo=MADRID)
    queue=(await db.execute(select(EditorialCandidate,Article.slug).outerjoin(Article,Article.id==EditorialCandidate.article_id)
        .order_by(case((EditorialCandidate.state.in_(['preparing','generating','needs_verification']),0),
                       (EditorialCandidate.state.in_(PENDING),1),else_=2),
                  EditorialCandidate.priority.desc(),EditorialCandidate.updated_at.desc()).limit(100))).all()
    counts=dict((await db.execute(select(EditorialCandidate.state,func.count()).group_by(EditorialCandidate.state))).all())
    candidate_reservations={}
    for row in rows:
        assigned=0
        for attempt in row.report.get('candidate_attempts',[]):
            amount=int(attempt.get('reserved_microusd',0));assigned+=amount
            if attempt.get('candidate_id'):candidate_reservations[attempt['candidate_id']]=candidate_reservations.get(attempt['candidate_id'],0)+amount
        active=row.report.get('active_candidate_id')
        if active:candidate_reservations[active]=candidate_reservations.get(active,0)+max(0,row.reserved_microusd-assigned)
    usage=(await db.execute(select(func.coalesce(func.sum(GenerationUsage.input_tokens),0),func.coalesce(func.sum(GenerationUsage.output_tokens),0),
        func.coalesce(func.sum(GenerationUsage.estimated_microusd),0),func.count(GenerationUsage.id),func.coalesce(func.sum(GenerationUsage.cached_tokens),0),func.min(GenerationUsage.created_at)).join(ResearchRun,ResearchRun.id==GenerationUsage.run_id)
        .where(ResearchRun.editorial_date>=month))).one()
    jobs=(await db.scalars(select(EditorialExecution).order_by(EditorialExecution.id.desc()).limit(20))).all()
    scans=(await db.scalars(select(NewsScan).order_by(NewsScan.window.desc()).limit(8))).all()
    phase_rows=(await db.execute(select(GenerationUsage.run_id,GenerationUsage.stage,func.sum(GenerationUsage.estimated_microusd),func.count()).group_by(GenerationUsage.run_id,GenerationUsage.stage).where(GenerationUsage.run_id.in_([r.id for r in rows])))).all()
    phases={}
    for rid,stage,cost,count in phase_rows:phases.setdefault(rid,[]).append({'stage':stage,'accounted_microusd':cost,'reported_calls':count,'billing_verified':False})
    published_count=await db.scalar(select(func.count(Article.id)).where(Article.status=='published'))
    completed_jobs=await db.scalar(select(func.count(EditorialExecution.id)).where(EditorialExecution.state=='completed'))
    verified_articles=await db.scalar(select(func.count(func.distinct(EditorialCandidate.article_id))).join(Article,Article.id==EditorialCandidate.article_id).where(
        EditorialCandidate.state=='published',Article.status=='published',
        *[EditorialCandidate.details['verification'][k].as_boolean().is_(True) for k in ['api','html','seo','sitemap']]))
    publication_events=await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action=='publication_verified'))
    lane_rows=(await db.scalars(select(EditorialLaneRun).where(EditorialLaneRun.run_id.in_([r.id for r in rows])))).all()
    lane_views={}
    for lane in lane_rows:
        parent=next(r for r in rows if r.id==lane.run_id)
        summary=next((s for s in parent.report.get('lanes',[]) if s.get('engine')==lane.engine and s.get('slot',1)==lane.slot),{})
        lane_views.setdefault(lane.run_id,[]).append({'engine':lane.engine,'slot':lane.slot,'status':lane.status,
            'reason':lane.reason,'candidate_id':lane.candidate_id,'article_id':lane.article_id,
            'reported_cost_microusd':summary.get('reported_cost_microusd'),'report':report_view(lane.report)})
    return {'editorial_target':{'news':1,'practical':config.practical_publications,'total':1+config.practical_publications,
            'guaranteed':False,'active':config.two_lanes},
        'rapid':{'enabled':False,'retired':True,'worker_alive':False,'interval_minutes':None,'model_calls_per_scan':0,
        'scans':[{'id':s.id,'window':s.window,'state':s.state,'finished_at':s.finished_at,'report':s.report} for s in scans]},
        'executions':[execution_view(j) for j in jobs],'enabled': bool(control and control.enabled), 'configured': bool(config.api_key.get_secret_value()), 'worker_alive': worker_alive,
        'content_counts':{'published_articles':published_count,'verified_published_articles':verified_articles,
            'completed_manual_executions':completed_jobs,'verified_publication_events':publication_events,'scope':'articles_current_events_historical'},
        'health':health,'remaining_reservation_usd':{'monthly':f'{max(0,int(config.monthly_usd*1_000_000)-reserved)/1_000_000:.6f}',
            'daily':f'{max(0,int(config.daily_usd*1_000_000)-day_reserved)/1_000_000:.6f}'},'daily_reserved_usd':f'{day_reserved/1_000_000:.6f}',
        'model': config.model, 'at': config.at.strftime('%H:%M'), 'timezone': 'Europe/Madrid',
        'auto_publish': config.auto_publish, 'monthly_usd': str(config.monthly_usd), 'daily_usd': str(config.daily_usd),
        'reserved_usd': f'{reserved / 1_000_000:.6f}', 'feeds': [f.url for f in FEEDS],
        'next_execution':upcoming.isoformat(),'weekly_target':{'min':None,'max':None,'guaranteed':False},'research_tool':{'type':'web_search','maximum_calls':1,'usd_per_call':'0.01','billing_verified':False},
        'queue_counts':counts,'queue_truncated':sum(counts.values())>len(queue),'reported_usage':{'input_tokens':usage[0],'output_tokens':usage[1],
            'estimated_usd':f'{usage[2]/1_000_000:.6f}','billing_verified':False,'billed_usd':None,
            'reported_calls':usage[3],'cached_input_tokens':usage[4],'first_recorded_at':usage[5]},
        'queue':[{'id':c.id,'topic':c.topic,'engine':c.engine,'kind':c.kind,'section':c.section,'intent':c.intent,'keyword':c.keyword,
            'priority':c.priority,'state':c.state,'reason':c.reason,'attempts':c.attempts,'article_url':'/articulos/'+slug if slug and c.state=='published' else None,
            'recovery':disposition(c),
            'demand_source':c.details.get('demand_source','unknown'),
            'opportunity':c.details.get('opportunity'),'usage_events':c.details.get('usage_events',[]),
            'queue_audit':c.details.get('queue_audit'),
            'reserved_microusd':candidate_reservations.get(c.id,0),'reservation_scope':'last_14_runs',
            'unreported_usage_calls':int(c.details.get('unreported_usage_calls',0)),
            'source_count':len(c.details.get('evidence') or c.details.get('sources') or []),
            'verification_mode':c.details.get('selection',{}).get('verification_mode'),
            'source_urls':[s if isinstance(s,str) else s.get('url','') for s in (c.details.get('evidence') or c.details.get('sources') or [])][:8],
            'verified_examples':bool(c.details.get('verification'))} for c,slug in queue],
        'runs': [{'id': r.id, 'date': r.editorial_date.isoformat(), 'status': r.status, 'reason': r.reason,
                  'article_id': r.article_id, 'reserved_usd': f'{r.reserved_microusd / 1_000_000:.6f}',
                  'report': report_view(r.report), 'lanes':lane_views.get(r.id,[]),'phase_usage':phases.get(r.id,[]), 'finished_at': r.finished_at} for r in rows]}


@router.patch('')
async def update_control(payload: ControlWrite, db: DB, actor: Annotated[str, Depends(require_editor)]):
    row = await db.scalar(select(ResearchControl).where(ResearchControl.id == 1).with_for_update())
    if row is None:
        raise HTTPException(503, 'Aplica las migraciones antes de configurar la investigación')
    if payload.rapid_enabled:raise HTTPException(422,'La investigación automática se ejecuta únicamente a las 22:30 Europe/Madrid')
    row.enabled = payload.enabled
    row.rapid_enabled=False
    db.add(AuditLog(actor=actor, action='research_control', entity_type='research', entity_id=1, details={'enabled': row.enabled,'rapid_enabled':row.rapid_enabled}))
    await db.commit()
    return {'enabled': row.enabled,**({'rapid_enabled':row.rapid_enabled} if payload.rapid_enabled is not None else {})}


class SearchSignal(BaseModel):
    model_config=ConfigDict(extra='forbid')
    query: str=Field(min_length=3,max_length=150,pattern=r'^[^@<>\r\n]+$')
    impressions:int=Field(ge=0,le=1_000_000_000)
    clicks:int=Field(ge=0,le=1_000_000_000)
    position:float=Field(ge=0,le=1000,allow_inf_nan=False)
    @model_validator(mode='after')
    def consistent(self):
        if self.clicks>self.impressions:raise ValueError('Los clics no pueden superar las impresiones')
        return self


class SearchSignals(BaseModel):
    model_config=ConfigDict(extra='forbid')
    source: str=Field(pattern=r'^search_console_export$')
    signals:list[SearchSignal]=Field(max_length=100)


@router.post('/signals')
async def import_signals(payload:SearchSignals,db:DB,actor:Annotated[str,Depends(require_editor)]):
    rows=(await db.scalars(select(EditorialCandidate).where(EditorialCandidate.state.in_(['queued','ready','deferred','published'])).limit(200))).all()
    matched=0
    from app.research.writing import normalize
    for candidate in rows:
        terms=set(normalize(candidate.keyword).split())
        signal=next((s for s in payload.signals if len(terms & set(normalize(s.query).split()))>=3 and s.clicks<=s.impressions),None)
        if not signal:continue
        candidate.priority=min(95,70+min(20,signal.impressions//100)+min(5,signal.clicks//10))
        candidate.details=dict(candidate.details,demand_source='search_console_export',demand={'query':signal.query,'impressions':signal.impressions,'clicks':signal.clicks,'position':signal.position,
            'ctr':signal.clicks/signal.impressions if signal.impressions else None,'imported_at':utcnow().isoformat(),
            'country':None,'search_volume':None})
        matched+=1
    db.add(AuditLog(actor=actor,action='editorial_signals_import',entity_type='research',entity_id=1,details={'matched':matched,'signals':len(payload.signals)}))
    await db.commit();return {'matched':matched,'source':'search_console_export'}
