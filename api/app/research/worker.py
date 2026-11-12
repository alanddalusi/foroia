"""Trabajador persistente. Una ejecución/día, sin reintentos de cobros inciertos."""
import asyncio
import copy
import hashlib
import json
import secrets
import sys
from datetime import datetime,timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.db import get_sessionmaker
from app.core.limits import get_redis
from app.models import Article, AuditLog, ResearchControl, ResearchRun, utcnow
from app.research.config import MADRID, due, settings
from app.research.sources import collect, restore, independent_organizations
from app.research.writing import StopRun, generate

LOCK = 'foroia:research:worker'
RELEASE = "if redis.call('GET',KEYS[1]) == ARGV[1] then return redis.call('DEL',KEYS[1]) end return 0"


async def carry_review(db, run):
    """Una revisión pendiente ocupa la ejecución del nuevo día; nunca duplica artículo."""
    rows = (await db.scalars(select(ResearchRun).where(
        ResearchRun.editorial_date < run.editorial_date,
        ResearchRun.created_at >= utcnow() - timedelta(hours=48),
        ResearchRun.status == 'draft',
        ResearchRun.reason.in_(['incomplete_generation', 'provider_unavailable', 'budget_exhausted']),
    ).order_by(ResearchRun.editorial_date.desc()).limit(14).with_for_update())).all()
    for old in rows:
        report = old.report
        if report.get('carried_from_run') or report.get('carried_to_run') or not old.article_id or not report.get('pending_review') or not report.get('evidence') or report.get('proposal') != report.get('evidence'):
            continue
        article = await db.get(Article, old.article_id)
        if not article or article.status != 'draft':
            continue
        run.article_id = old.article_id
        run.report = {k: report[k] for k in ('proposal', 'evidence', 'sources', 'corrections_used', 'versions', 'selection') if k in report}
        run.report = dict(run.report, pending_review=True, carried_from_run=old.id)
        old.report = dict(report, carried_to_run=run.id)
        db.add(AuditLog(actor='automation', action='research_carry_review', entity_type='research', entity_id=run.id, details={'previous_run': old.id}))
        return True
    return False


async def enabled(db):
    row = await db.get(ResearchControl, 1, populate_existing=True)
    return row is not None and row.enabled


async def reserve(db, run, config, cost):
    if type(cost) is not int or cost<0:raise ValueError('Invalid reservation')
    budget_run=getattr(run,'budget_run',run)
    control = await db.scalar(select(ResearchControl).where(ResearchControl.id == 1).with_for_update().execution_options(populate_existing=True))
    if not control or not control.enabled:
        raise StopRun('paused')
    # Reload after the control-row lock: different sessions must see the last reservation.
    await db.refresh(budget_run,attribute_names=['reserved_microusd'])
    month = budget_run.editorial_date.replace(day=1)
    total = await db.scalar(select(func.coalesce(func.sum(ResearchRun.reserved_microusd), 0)).where(ResearchRun.editorial_date >= month))
    protected=0
    if hasattr(run,'lane') and (run.lane.engine=='news' or config.practical_publications==2):
        await db.refresh(budget_run,attribute_names=['report'])
        protected=int(budget_run.report.get('practical_headroom_microusd',0))
    if budget_run.reserved_microusd + cost + protected > int(config.daily_usd * 1_000_000) or total + cost + protected > int(config.monthly_usd * 1_000_000):
        raise StopRun('budget_exhausted')
    if hasattr(run,'execution'):
        job=run.execution
        if job.reserved_microusd+cost>job.max_reserved_microusd:raise StopRun('execution_budget_exhausted')
        count=int(job.report.get('reserved_calls',0))
        if count>=job.prepared['max_calls']:raise StopRun('execution_call_limit')
        job.reserved_microusd+=cost
        job.report=dict(job.report,reserved_calls=count+1)
    budget_run.reserved_microusd += cost
    await db.commit()  # Persistir ANTES de efectuar una llamada facturable.


async def pipeline(db, run, config, redis, token, collector=collect, generator=generate, resume=False,policy=None,candidate=None):
    existing = (await db.scalars(select(Article).order_by(Article.id.desc()).limit(300))).all()
    # Todos los enlaces históricos, sin cargar todos los cuerpos en memoria.
    urls = set()
    stream = await db.stream_scalars(select(Article.sources).execution_options(yield_per=100))
    async for sources in stream:
        urls.update(s['url'].split('?')[0].rstrip('/') for s in sources)
    # Reserve two document slots for targeted discovery or the next candidate.
    if collector is collect and not resume:
        evidence, stats = await collector(utcnow(), urls, initial_document_limit=6)
    else:
        evidence, stats = await collector(utcnow(), urls)
    if not resume and not policy:
        from app.research.selection import select as select_topic
        from app.research.sources import recover_related
        selected, selection = select_topic(evidence)
        if not selected:
            before_recovery = selection
            evidence, stats = await recover_related(evidence, stats)
            selected, selection = select_topic(evidence)
            selection['before_recovery'] = before_recovery
        run.report = dict(run.report, **stats, selection=selection,
            sources=[{k:v for k,v in s.items() if k!='text'} for s in evidence])
        await db.commit()
        if not selected:
            raise StopRun('insufficient_sources' if len(evidence) < 2 else 'insufficient_independent_topic_sources')
        evidence = selected
        from app.research.editorial_policy import policy_for
        policy = {'kind':'news', **policy_for(evidence)}
        # Pin this set through generation, correction and final cited-source validation.
        run.report = dict(run.report, selection=dict(selection, generation_calls_started=1))
    elif resume and run.report.get('selection'):
        from app.research.selection import select as select_topic
        selected, check = select_topic(evidence)
        if {s['id'] for s in selected} != {s['id'] for s in evidence}:
            run.report = dict(run.report, resumed_selection=check)
            await db.commit()
            raise StopRun('insufficient_independent_topic_sources')
        if not policy:
            from app.research.editorial_policy import policy_for
            policy = {'kind':'news', **policy_for(evidence)}
    run.report = dict(run.report, **stats, sources=[{k: v for k, v in s.items() if k != 'text'} for s in evidence])
    await db.commit()
    if len(independent_organizations(evidence)) < (policy or {}).get('min_organizations',2):
        raise StopRun('insufficient_sources')
    async def budget(cost):
        if await redis.get(LOCK) != token:
            raise StopRun('lock_lost')
        if policy and policy.get('operation')=='update' and run.reserved_microusd-operation_start+cost>policy.get('max_operation_microusd',60000):
            raise StopRun('maintenance_budget_exhausted')
        await reserve(db, run, config, cost)
    operation_start=run.reserved_microusd
    from app.research.quality import prepare
    if candidate and candidate.target_article_id:
        existing=[a for a in existing if a.id!=candidate.target_article_id]
    article, article_data = await prepare(db, run, config, evidence, existing, budget, generator, resume=resume,policy=policy)
    control = await db.scalar(select(ResearchControl).where(ResearchControl.id == 1).with_for_update().execution_options(populate_existing=True))
    if not control or not control.enabled:
        raise StopRun('paused')
    if await redis.get(LOCK) != token:
        raise StopRun('lock_lost')
    if candidate:
        # The nightly coordinator may publish several verified topics within the
        # same run/budget. Event identity and the final locked transaction remain.
        from app.models import EditorialCandidate
        locked_candidate=await db.scalar(select(EditorialCandidate).where(
            EditorialCandidate.id==candidate.id).with_for_update().execution_options(populate_existing=True))
        if not locked_candidate or locked_candidate.state!='generating':raise StopRun('duplicate_publication')
        from app.research.quota import check_quota
        await check_quota(db,config,locked_candidate,utcnow(),getattr(run,'execution',None))
    article = await db.scalar(select(Article).where(Article.id == run.article_id).with_for_update().execution_options(populate_existing=True))
    snapshot = article_data.model_dump(mode='json')
    if not article or article.status != 'draft' or any(getattr(article, key) != value for key, value in snapshot.items()):
        raise StopRun('article_changed')
    # Una transacción final incluye visibilidad, auditoría y resultado diario.
    if candidate and candidate.target_article_id:
        target=await db.scalar(select(Article).where(Article.id==candidate.target_article_id).with_for_update().execution_options(populate_existing=True))
        from app.research.publication import article_snapshot
        before=candidate.details.get('target_snapshot')
        if not target or target.status!='published' or article_snapshot(target)!=before:raise StopRun('article_changed')
        old=article_snapshot(target)
        for key,value in snapshot.items():
            if key not in {'slug','author_name'}:setattr(target,key,value)
        article.status='archived'
        candidate.details=dict(candidate.details,previous_revision=old)
        article=target
        run.article_id=article.id
    from app.modules.articles.media import ensure_media
    await ensure_media(db,article,run.report.get('evidence_catalogue',[]))
    article.status = 'published' if config.auto_publish else 'review'
    article.reviewed_by = 'automation' if config.auto_publish else None
    article.reviewed_at = utcnow() if config.auto_publish else None
    if not (candidate and candidate.target_article_id):
        article.published_at = utcnow() if config.auto_publish else None
    run.status = 'published' if config.auto_publish else 'review'
    run.reason, run.finished_at = 'quality_checks_passed', utcnow()
    run.report=dict(run.report,pending_review=False,current_stage='published' if config.auto_publish else 'review')
    db.add(AuditLog(actor='automation', action='auto_publish' if config.auto_publish else 'auto_review', entity_type='article', entity_id=article.id, details={'run_id': run.id, 'human_review': False}))
    if candidate:
        from app.research.publication import article_snapshot
        await db.flush()
        candidate.article_id=article.id
        candidate.state='needs_verification' if config.auto_publish else 'ready'
        candidate.details=dict(candidate.details,publication_snapshot=article_snapshot(article),verification_attempts=0)
    await db.commit()


async def tick(force=False,max_publications=None):
    redis = get_redis()
    await redis.set('foroia:research:heartbeat', utcnow().isoformat(), ex=90)
    config = settings()
    day = utcnow().astimezone(MADRID).date() if force else due(utcnow(), config)
    if day is None or not config.api_key.get_secret_value():
        return
    token = secrets.token_hex(24).encode()
    if not await redis.set(LOCK, token, nx=True, ex=1800):
        return
    try:
        async with get_sessionmaker()() as db:
            if not await enabled(db):
                return
            # Un proceso muerto no vuelve a gastar ni publicar tras reinicio.
            stale = (await db.scalars(select(ResearchRun).where(ResearchRun.status == 'running', ResearchRun.created_at < utcnow() - timedelta(minutes=30)))).all()
            for row in stale:
                row.status, row.reason, row.finished_at = 'interrupted', 'worker_interrupted', utcnow()
            await db.commit()
            run=await db.scalar(select(ResearchRun).where(ResearchRun.editorial_date==day))
            if run:
                recovering_lanes=config.two_lanes and run.report.get('lanes_version')==1 and not run.report.get('lanes_complete')
                if not recovering_lanes and (not run.report.get('budget_bucket') or run.report.get('nightly_started')):return
                from app.models import EditorialCandidate
                if not recovering_lanes and await db.scalar(select(EditorialCandidate.id).join(Article,Article.id==EditorialCandidate.article_id).where(
                    Article.status=='published',Article.published_at>=datetime.combine(day,datetime.min.time(),tzinfo=MADRID)).limit(1)):return
                run.report=dict(run.report,nightly_started=True)
                run.status='running';run.reason='';run.finished_at=None;run.article_id=None
            else:
                run = ResearchRun(editorial_date=day, status='running', reason='', report={'nightly_started':True}, reserved_microusd=0)
                db.add(run)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                return
            run_id = run.id
            if force:
                db.add(AuditLog(actor='operator',action='research_manual_day',entity_type='research',entity_id=run_id,
                    details={'maximum_publications':max_publications,'same_daily_budget':True,'consumes_editorial_day':True}))
                await db.commit()
            print(json.dumps({'event':'editorial_run_started','run_id':run_id,'editorial_date':str(day),'timezone':'Europe/Madrid'}),flush=True)
            try:
                from app.research.editorial import execute
                if config.two_lanes and max_publications is None:
                    from app.research.lanes import execute as execute_lanes
                    operation=execute_lanes(db,run,config,redis,token,news_collector=collect)
                else:operation=execute(db,run,config,redis,token,max_publications=max_publications) if max_publications is not None else execute(db,run,config,redis,token)
                await asyncio.wait_for(operation,timeout=1200 if config.two_lanes and config.practical_publications==2 else 900)
            except Exception as exc:
                await db.rollback()
                run = await db.get(ResearchRun, run_id, populate_existing=True)
                reason = str(exc) if isinstance(exc, StopRun) else 'timeout' if isinstance(exc, TimeoutError) else 'internal_error'
                if config.two_lanes and run.report.get('lanes_version')==1:
                    from app.research.lanes import summarize
                    await summarize(db,run)
                    run.report=dict(run.report,halted_reason=reason)
                else:run.status = 'draft' if run.article_id else 'skipped'
                run.reason = reason
                run.finished_at = utcnow()
                await db.commit()
            # Material de investigación privado durante 30 días; historial económico persistente.
            old = (await db.scalars(select(ResearchRun).where(ResearchRun.created_at < utcnow() - timedelta(days=30), ResearchRun.report != {}))).all()
            for row in old:
                row.report = {}
            from app.models import EditorialLaneRun
            old_lanes=(await db.scalars(select(EditorialLaneRun).where(
                EditorialLaneRun.created_at<utcnow()-timedelta(days=30),EditorialLaneRun.report!={}))).all()
            for lane in old_lanes:lane.report={}
            await db.commit()
            print(json.dumps({'event':'editorial_run_finished','run_id':run_id,'editorial_date':str(day),
                'status':run.status,'reason':run.reason,'article_id':run.article_id,'reserved_microusd':run.reserved_microusd}),flush=True)
    finally:
        await redis.eval(RELEASE, 1, LOCK, token)


async def retry_failed(run_id):
    """Operator-only, single audited retry of a completed evidence rejection.

    Never used by the scheduler. Keep the same date, cumulative reservation and
    original report. Uncertain provider failures and existing articles are ineligible.
    """
    redis, config = get_redis(), settings()
    if not config.api_key.get_secret_value():
        raise StopRun('not_configured')
    token = secrets.token_hex(24).encode()
    if not await redis.set(LOCK, token, nx=True, ex=1800):
        raise StopRun('worker_busy')
    try:
        async with get_sessionmaker()() as db:
            if not await enabled(db):
                raise StopRun('paused')
            run = await db.scalar(select(ResearchRun).where(ResearchRun.id == run_id).with_for_update())
            today = utcnow().astimezone(MADRID).date()
            if (not run or run.editorial_date != today or run.status != 'skipped'
                    or run.reason != 'invalid_evidence' or not run.finished_at or run.article_id
                    or 'manual_retry' in run.report or 'prior_attempts' in run.report):
                raise StopRun('retry_not_eligible')
            previous = {'status': run.status, 'reason': run.reason, 'finished_at': run.finished_at.isoformat(),
                        'reserved_microusd': run.reserved_microusd, 'report': run.report}
            run.report = {'prior_attempts': [previous], 'manual_retry': {'started_at': utcnow().isoformat(),
                'original_reserved_microusd': run.reserved_microusd, 'limit': 1}}
            run.status, run.reason, run.finished_at = 'running', '', None
            db.add(AuditLog(actor='operator', action='research_manual_retry', entity_type='research',
                entity_id=run.id, details={'previous_reason': 'invalid_evidence', 'same_daily_budget': True}))
            await db.commit()
            try:
                await asyncio.wait_for(pipeline(db, run, config, redis, token), timeout=900)
            except Exception as exc:
                await db.rollback()
                run = await db.get(ResearchRun, run_id, populate_existing=True)
                run.status = 'draft' if run.article_id else 'skipped'
                run.reason = str(exc) if isinstance(exc, StopRun) else 'timeout' if isinstance(exc, TimeoutError) else 'internal_error'
                run.finished_at = utcnow()
                await db.commit()
    finally:
        await redis.eval(RELEASE, 1, LOCK, token)


async def retry_news(run_id, resume=False, fresh=False):
    """Explicit operator validation of new discovery; same day, budget and pipeline."""
    from app.models import EditorialExecution
    from app.research.executions import ACTIVE,allowance
    from app.research.night_web import payload,maximum
    if fresh and resume:raise ValueError('Choose saved recovery or fresh research')
    redis=get_redis();config=settings();token=secrets.token_hex(24).encode()
    if not config.api_key.get_secret_value():raise StopRun('not_configured')
    if not await redis.set(LOCK,token,nx=True,ex=1800):raise StopRun('worker_busy')
    try:
        async with get_sessionmaker()() as db:
            if not await enabled(db):raise StopRun('paused')
            run=await db.get(ResearchRun,run_id,populate_existing=True)
            day=utcnow().astimezone(MADRID).date()
            if not run or run.editorial_date!=day or run.status=='running':
                raise StopRun('news_retry_not_eligible')
            manual=run.report.get('manual_news_retry',{})
            if fresh:
                if not manual.get('result') or manual.get('fresh_authorized') or manual['result'].get('new_article_id') or (run.article_id and run.status!='published'):
                    raise StopRun('news_retry_not_eligible')
            elif bool(manual)!=resume:raise StopRun('news_retry_not_eligible')
            if await db.scalar(select(EditorialExecution.id).where(EditorialExecution.state.in_(ACTIVE)).limit(1)):
                raise StopRun('worker_busy')
            checkpoints=run.report.get('stage_checkpoints',{})
            if any(v.get('state') in {'reserving','calling','uncertain'} for v in checkpoints.values()):
                raise StopRun('uncertain_provider_result')
            web=run.report.get('web_research',{})
            if fresh and any(run.report.get(slot) and not run.report[slot].get('settled') for slot in ('web_research','alternative_web_research')):
                raise StopRun('uncertain_search_result')
            known_manual_bucket=False
            if not web and run.report.get('budget_bucket') and not resume:
                # Explicit operator-only new test after a completed recovery.
                # Same date and allowance; never called by the daily scheduler.
                completed=await db.scalar(select(EditorialExecution.id).join(Article,Article.id==EditorialExecution.article_id).where(
                    EditorialExecution.run_id==run.id,EditorialExecution.state=='completed',Article.status=='published').limit(1))
                known_manual_bucket=bool(completed)
            if not known_manual_bucket and (web.get('state')!='response' or not web.get('settled')):raise StopRun('uncertain_search_result')
            titles=(await db.scalars(select(Article.title).where(Article.status=='published').order_by(Article.id.desc()).limit(100))).all()
            from app.research.event_sources import drafting_headroom
            required=maximum(config,payload(config,utcnow(),titles))+(drafting_headroom(config) if fresh else 0)
            if not resume and required>await allowance(db,config,day):raise StopRun('budget_exhausted')
            previous={'status':run.status,'reason':run.reason,'article_id':run.article_id,
                'finished_at':run.finished_at.isoformat() if run.finished_at else None,
                'reserved_microusd':run.reserved_microusd,'report':copy.deepcopy(run.report)}
            if resume:
                if run.report['manual_news_retry'].get('result',{}).get('new_article_id') or run.article_id and run.status!='published':
                    raise StopRun('news_resume_not_eligible')
                # Reuse the settled response and its original ledger identity.
                # No new search, reservation reset or removal of history.
                history=list(run.report.get('news_continuations',[]))
                history.append({'at':utcnow().isoformat(),'discovery':copy.deepcopy(run.report.get('news_discovery',{})),
                    'result':copy.deepcopy(run.report['manual_news_retry'].get('result',{}))})
                run.report=dict(run.report,news_continuations=history)
            else:
                key=secrets.token_hex(16)
                run.report={'prior_attempts':[previous],'research_attempt_key':key,
                    'manual_news_retry':{'key':key,'started_at':utcnow().isoformat(),'news_only':True,'maximum_publications':1}}
                if fresh:run.report['manual_news_retry']['fresh_authorized']=True
            run.status='running';run.reason='';run.finished_at=None;run.article_id=None
            db.add(AuditLog(actor='operator',action='research_news_retry',entity_type='research',entity_id=run.id,
                details={'same_daily_budget':True,'preserved_previous_article_id':previous['article_id'],'news_only':True,'maximum_publications':1,'fresh_operator_attempt':fresh}))
            await db.commit()
            print(json.dumps({'event':'news_retry_started','run_id':run.id,'same_daily_budget':True}),flush=True)
            try:
                from app.research.editorial import execute
                await asyncio.wait_for(execute(db,run,config,redis,token,max_publications=1,allow_evergreen=False),900)
            except Exception as exc:
                await db.rollback();run=await db.get(ResearchRun,run_id,populate_existing=True)
                run.status='draft' if run.article_id else 'skipped'
                run.reason=str(exc) if isinstance(exc,StopRun) else 'timeout' if isinstance(exc,TimeoutError) else 'internal_error'
                run.finished_at=utcnow();await db.commit()
            new_article=run.article_id if run.status=='published' else None
            outcome={'status':run.status,'reason':run.reason,'new_article_id':new_article,'finished_at':utcnow().isoformat()}
            run.report=dict(run.report,manual_news_retry=dict(run.report['manual_news_retry'],result=outcome))
            if not run.article_id and previous['article_id']:
                old=await db.get(Article,previous['article_id'])
                if old and old.status=='published':
                    run.article_id=old.id;run.status='published';run.reason='news_retry_no_publication'
            run.finished_at=utcnow();await db.commit()
            print(json.dumps({'event':'news_retry_finished','run_id':run.id,'result':outcome,'reserved_microusd':run.reserved_microusd}),flush=True)
    finally:await redis.eval(RELEASE,1,LOCK,token)


async def resume_proposal(run_id, generator=generate, verifier=None):
    """Operator-only recovery of a stored proposal after a deterministic fix.

    No research or drafting call; source preflight, full review and publication
    remain the normal pipeline. Never clear consumed corrections or usage.
    """
    from app.models import EditorialCandidate, EditorialExecution
    from app.research.executions import ACTIVE
    from app.research.queue import prepare_candidate
    from app.research.evidence import index
    from app.research.writing import Draft, validate_draft, USAGE_SINK
    from app.research.editorial import usage_sink
    from app.research.publication import verify_candidate
    redis=get_redis();config=settings();token=secrets.token_hex(24).encode()
    if not config.api_key.get_secret_value():raise StopRun('not_configured')
    if not await redis.set(LOCK,token,nx=True,ex=1800):raise StopRun('worker_busy')
    try:
        async with get_sessionmaker()() as db:
            run=await db.get(ResearchRun,run_id,populate_existing=True)
            if not run or run.status!='skipped' or run.article_id or run.editorial_date!=utcnow().astimezone(MADRID).date() or not await enabled(db):raise StopRun('proposal_recovery_not_eligible')
            if await db.scalar(select(EditorialExecution.id).where(EditorialExecution.state.in_(ACTIVE)).limit(1)):raise StopRun('worker_busy')
            manual=run.report.get('manual_news_retry',{})
            attempts=run.report.get('candidate_attempts',[])
            if manual.get('proposal_recovery_started') or not attempts:raise StopRun('proposal_recovery_not_eligible')
            last=attempts[-1];saved=copy.deepcopy(last.get('report',{}))
            candidate=await db.get(EditorialCandidate,last.get('candidate_id'))
            if not candidate or candidate.state!='rejected' or candidate.reason!='official_scope_requires_corroboration' or candidate.article_id or not saved.get('proposal') or saved.get('review'):
                raise StopRun('proposal_recovery_not_eligible')
            if any(e.get('state') in {'reserving','calling','uncertain'} for e in saved.get('stage_checkpoints',{}).values()):raise StopRun('uncertain_provider_result')
            sources=saved.get('evidence_catalogue',[]);index(sources)
            chosen,policy=await prepare_candidate(db,candidate,utcnow(),{'remaining':0})
            if {(s['id'],s['content_sha256']) for s in chosen}!={(s['id'],s['content_sha256']) for s in sources}:raise StopRun('evidence_source_changed')
            policy=saved['policy'];draft=Draft.model_validate(saved['proposal'])
            existing=(await db.scalars(select(Article).where(Article.status=='published'))).all()
            validate_draft(draft,sources,existing,policy,provisional=True)
            original=copy.deepcopy(run.report)
            run.report=dict(saved,news_discovery=original.get('news_discovery',{}),candidate_attempts=attempts,
                manual_news_retry=dict(manual,proposal_recovery_started=utcnow().isoformat()),
                current_stage='review',proposal_recovery={'candidate_id':candidate.id,'reason':'VS Code is a product name, not versus','draft_sha256':hashlib.sha256(json.dumps(draft.model_dump(),sort_keys=True).encode()).hexdigest()})
            run.status='running';run.reason='';run.finished_at=None;candidate.state='generating'
            db.add(AuditLog(actor='operator',action='research_saved_proposal_recovery',entity_type='research',entity_id=run.id,details={'candidate_id':candidate.id,'no_research_or_drafting':True}))
            await db.commit()
            async def collector(now,urls):return sources,{'candidate_count':len(sources),'fetch_failures':0}
            async def saved_generator(config,schema,instructions,data,budget):
                if schema is Draft:
                    if data.get('errors'):raise StopRun('correction_limit_reached')
                    return draft.model_copy(deep=True)
                return await generator(config,schema,instructions,data,budget)
            sink=USAGE_SINK.set(lambda c,s,u:usage_sink(db,run,candidate,c,s,u))
            try:
                await pipeline(db,run,config,redis,token,collector,saved_generator,policy=policy,candidate=candidate)
                passed=await verify_candidate(db,candidate,verifier=verifier)
                run.status='published' if passed else 'published' if candidate.state=='needs_verification' else 'skipped'
                run.reason='quality_checks_passed' if passed else 'publication_verification_pending' if candidate.state=='needs_verification' else candidate.reason
                run.report=dict(run.report,verification=candidate.details.get('verification'),publications=[{'candidate_id':candidate.id,'article_id':candidate.article_id,'url':candidate.details.get('verification',{}).get('url')}] if passed else [])
            except Exception as exc:
                await db.rollback();run=await db.get(ResearchRun,run_id,populate_existing=True);candidate=await db.get(EditorialCandidate,last['candidate_id'],populate_existing=True)
                run.status='draft' if run.article_id else 'skipped';run.reason=str(exc) if isinstance(exc,StopRun) else 'candidate_internal_error'
                candidate.article_id=run.article_id;candidate.state='deferred' if run.article_id else 'rejected';candidate.reason=run.reason
                if run.report.get('pending_review'):candidate.details=dict(candidate.details,resume_report=copy.deepcopy(run.report))
            finally:USAGE_SINK.reset(sink)
            run.finished_at=utcnow()
            run.report=dict(run.report,manual_news_retry=dict(run.report['manual_news_retry'],result={'status':run.status,'reason':run.reason,'new_article_id':run.article_id if run.status=='published' else None,'finished_at':run.finished_at.isoformat()}))
            await db.commit()
            print(json.dumps({'event':'proposal_recovery_finished','run_id':run.id,'status':run.status,'reason':run.reason,'article_id':run.article_id,'reserved_microusd':run.reserved_microusd}),flush=True)
    finally:await redis.eval(RELEASE,1,LOCK,token)


async def main():
    if len(sys.argv)==3 and sys.argv[1]=='--resume-proposal-run':
        run_id=int(sys.argv[2])
        if run_id<=0:raise ValueError('positive run ID required')
        await resume_proposal(run_id);return
    if len(sys.argv)==3 and sys.argv[1]=='--new-news-attempt':
        run_id=int(sys.argv[2])
        if run_id<=0:raise ValueError('positive run ID required')
        await retry_news(run_id,fresh=True);return
    if len(sys.argv)==3 and sys.argv[1]=='--resume-news-run':
        run_id=int(sys.argv[2])
        if run_id<=0:raise ValueError('positive run ID required')
        await retry_news(run_id,resume=True);return
    if len(sys.argv)==3 and sys.argv[1]=='--retry-news-run':
        run_id=int(sys.argv[2])
        if run_id<=0:raise ValueError('positive run ID required')
        await retry_news(run_id);return
    if len(sys.argv) == 3 and sys.argv[1] == '--retry-failed-run':
        run_id = int(sys.argv[2])
        if run_id <= 0:
            raise ValueError('positive run ID required')
        await retry_failed(run_id)
        return
    if '--once' in sys.argv:
        maximum=None
        if '--max-publications' in sys.argv:
            maximum=int(sys.argv[sys.argv.index('--max-publications')+1])
            if not 1<=maximum<=6:raise ValueError('publication limit must be between one and six')
        await tick(force=True,max_publications=maximum)
        return
    async def heartbeat():
        while True:
            try:
                await get_redis().set('foroia:research:heartbeat', utcnow().isoformat(), ex=90)
            except Exception:
                pass
            await asyncio.sleep(30)
    task = asyncio.create_task(heartbeat())
    try:
        while True:
            try:
                from app.research.editorial import reconcile_publications
                await reconcile_publications()
                from app.research.executions import process_next
                await process_next()
                await tick()
            except Exception:
                print('Investigación temporalmente no disponible; consultar panel.', flush=True)
            await asyncio.sleep(30)
    finally:
        task.cancel()


if __name__ == '__main__':
    asyncio.run(main())
