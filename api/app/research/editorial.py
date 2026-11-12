"""Daily autonomous coordinator. News and evergreen share money, not failure state."""
import copy
from datetime import UTC,datetime,timedelta
from decimal import Decimal

from sqlalchemy import select,func,case
from app.models import Article,EditorialCandidate,EditorialLaneRun,GenerationUsage,ResearchControl,ResearchRun,AuditLog,utcnow
from app.research.config import MADRID
from app.research.documents import aware
from app.research.queue import seed_evergreen,discover_news,prepare_candidate,defer_or_reject,fingerprint,discover_document_opportunities,focused_document
from app.research.sources import collect,recover_related,SourceError
from app.research.selection import select as select_topic
from app.research.writing import StopRun,generate,USAGE_SINK,normalize as writing_normalize
from app.research.publication import article_snapshot,verify_candidate
from app.research.recovery import PENDING, preserve

import re as _re
_STOP={'como','cómo','para','con','una','unos','unas','los','las','del','que','qué','sin','antes','desde','cero','sus','por','entre','sobre','tus','api','apis','python'}


def topic_words(text):
    """Meaningful words for contextual internal links (no stopwords or generic terms)."""
    return {w for w in _re.findall(r'[a-záéíóúñü0-9]+',text.lower()) if len(w)>3 and w not in _STOP}

async def usage_sink(db,run,candidate,config,stage,usage):
    ledger_key=usage.get('_ledger_key')
    if ledger_key and await db.scalar(select(GenerationUsage.id).where(GenerationUsage.request_key==ledger_key)):
        from app.research.checkpoints import settle_completed
        await settle_completed(db,run,config)
        return
    # Missing usage means unknown consumption, never a fabricated zero-dollar call.
    try:
        incoming,outgoing,cached=int(usage['input_tokens']),int(usage['output_tokens']),int((usage.get('input_tokens_details') or {}).get('cached_tokens',0))
        if not 0<=cached<=incoming<=10_000_000 or not 0<=outgoing<=100_000:raise ValueError()
    except (KeyError,TypeError,ValueError):
        if ledger_key and ledger_key in candidate.details.get('unknown_usage_keys',[]):return
        candidate.details=dict(candidate.details,unreported_usage_calls=int(candidate.details.get('unreported_usage_calls',0))+1)
        if ledger_key:candidate.details=dict(candidate.details,unknown_usage_keys=[*candidate.details.get('unknown_usage_keys',[]),ledger_key][-20:])
        await db.commit();return
    # Only the documented tariff for the currently deployed model is pinned here.
    # Reservations still charge every input token at the full configured rate.
    cache_rate=Decimal('0.025') if config.model=='gpt-5-mini' and config.input_per_million==Decimal('0.25') else config.input_per_million
    cost=int((Decimal(incoming-cached)*config.input_per_million+Decimal(cached)*cache_rate+Decimal(outgoing)*config.output_per_million).to_integral_value(rounding='ROUND_CEILING'))
    try:reasoning=int((usage.get('output_tokens_details') or {}).get('reasoning_tokens'))
    except (TypeError,ValueError):reasoning=None
    if reasoning is not None and not 0<=reasoning<=outgoing:reasoning=None
    event={'run_id':run.id,'stage':stage[:24],'input_tokens':incoming,'cached_tokens':cached,
        'output_tokens':outgoing,'reasoning_tokens':reasoning,'estimated_microusd':cost,
        'cost_basis':'reported_tokens_with_cache_tariff' if cache_rate!=config.input_per_million else 'reported_tokens_full_input_tariff',
        'at':utcnow().isoformat()}
    candidate.details=dict(candidate.details,usage_events=[*candidate.details.get('usage_events',[]),event][-20:])
    db.add(GenerationUsage(run_id=run.id,candidate_id=candidate.id,model=config.model,stage=stage[:24],request_key=ledger_key,
        input_tokens=incoming,output_tokens=outgoing,cached_tokens=cached,estimated_microusd=cost))
    await db.commit()
    from app.research.checkpoints import settle_completed
    await settle_completed(db,run,config)


async def recover_queue(db,now):
    rows=(await db.scalars(select(EditorialCandidate).where(EditorialCandidate.state.in_(['preparing','generating']),
        EditorialCandidate.updated_at<now-timedelta(minutes=30)).limit(30))).all()
    for row in rows:
        if row.state=='preparing':row.state='queued';row.reason='preflight_interrupted'
        else:
            run=await db.scalar(select(ResearchRun).where(ResearchRun.article_id==row.article_id).order_by(ResearchRun.id.desc()).limit(1)) if row.article_id else None
            if not run:
                run=await db.scalar(select(ResearchRun).where(ResearchRun.report['active_candidate_id'].as_integer()==row.id).order_by(ResearchRun.id.desc()).limit(1))
            lane=await db.scalar(select(EditorialLaneRun).where(EditorialLaneRun.candidate_id==row.id).order_by(EditorialLaneRun.id.desc()).limit(1))
            if lane:run=lane
            # Unknown paid results never restart drafting automatically after a crash.
            if run and run.report.get('pending_review') and run.report.get('proposal')==run.report.get('evidence'):
                row.article_id=run.article_id
                row.details=dict(row.details,resume_report=run.report)
                row.state='deferred';row.reason='incomplete_generation';row.next_attempt_at=now
            else:row.state='technical_error';row.reason='interrupted_uncertain_generation'
    await db.commit()


async def discover_updates(db,now,fetch_budget=None,doc_loader=None):
    """Only articles owned by this engine; never silently rewrite manual publications."""
    from app.models import SourceCache
    from app.research.blueprints import BY_KEY
    rows=(await db.scalars(select(EditorialCandidate).where(EditorialCandidate.engine=='evergreen',
        EditorialCandidate.state=='published',EditorialCandidate.target_article_id.is_(None),
        EditorialCandidate.published_at<now-timedelta(days=30)).limit(30))).all()
    if rows and fetch_budget is not None:
        from app.research.documents import official_document
        loader=doc_loader or official_document
        urls={s.get('raw_document_url',s['url']) for row in rows for s in row.details.get('evidence',[])}
        caches=(await db.scalars(select(SourceCache).where(SourceCache.url.in_(urls),SourceCache.expires_at<now).order_by(SourceCache.fetched_at).limit(2))).all()
        for cached in caches:
            try:await loader(db,cached.url,now,fetch_budget)
            except (SourceError,OSError,ValueError):pass
    for row in rows:
        blueprint=BY_KEY.get(row.details.get('blueprint'))
        if not blueprint and not row.details.get('focus'):continue
        changed=[]
        proposal=row.details.get('editorial_record',{}).get('proposal',{})
        quotes=[ref['quote'] for p in proposal.get('paragraphs',[]) for ref in p.get('evidence',[])]
        for old in row.details.get('evidence',[]):
            cached=await db.get(SourceCache,old.get('raw_document_url',old['url']))
            if cached and old.get('focus_key'):
                try:new_document=focused_document(cached.document,old['focus_key'])
                except StopRun:continue
                new_hash=new_document['content_sha256']
            else:new_document=cached.document if cached else {};new_hash=cached.content_sha256 if cached else ''
            if cached and not new_document.get('error') and new_hash!=old.get('content_sha256'):
                own=[ref['quote'] for p in proposal.get('paragraphs',[]) for ref in p.get('evidence',[]) if ref['source_id']==old['id']]
                if own and any(writing_normalize(q) not in writing_normalize(new_document['text']) for q in own):changed.append(new_hash)
        if not changed:continue
        from app.research.queue import insert_once
        article=await db.get(Article,row.article_id)
        if not article or article.status!='published':continue
        await insert_once(db,fingerprint=fingerprint('update:'+str(row.article_id)+':'+','.join(sorted(changed))),
            engine='evergreen',kind='update',topic=row.topic,section=row.section,intent=row.intent,keyword=row.keyword,
            priority=max(85,min(95,row.priority+5)),state='queued',target_article_id=article.id,
            details={'blueprint':blueprint.key if blueprint else None,'focus':row.details.get('focus'),'target_snapshot':article_snapshot(article),
                     'sources':list(blueprint.docs) if blueprint else [row.details['focus']['url']],
                     'previous_evidence_quotes':quotes,'demand_source':'verified_document_change'})


async def execute(db,run,config,redis,token,news_collector=collect,doc_loader=None,generator=generate,verifier=None,receipt_path=None,max_publications=1,allow_evergreen=True,_lane_engine=None):
    if max_publications is not None and (type(max_publications) is not int or not 1<=max_publications<=6):
        raise ValueError('Invalid publication limit')
    from app.research import worker
    run_id=run.id
    lane_id=run.lane.id if _lane_engine else None
    previous_history=copy.deepcopy(run.report.get('candidate_attempts',[])) if _lane_engine else []
    context={k:copy.deepcopy(run.report[k]) for k in ['prior_attempts','manual_news_retry','research_attempt_key','news_continuations'] if k in run.report}
    now=utcnow();await recover_queue(db,now);await seed_evergreen(db)
    from app.research.recovery import recover_known_failures
    await recover_known_failures(db,now)
    from app.research.queue import recover_verified_examples
    await recover_verified_examples(db,now,receipt_path)
    await discover_document_opportunities(db,now)
    discovery={}; web_state={}
    try:
        if _lane_engine=='evergreen':
            discovery={'reason':'independent_practical_line'}
        elif news_collector is collect:
            from app.research.night_web import discover
            discovery=await discover(db,run,config,redis,token,now)
            web_state=run.report.get('web_research',{})
        else:
            # Dependency injection for isolated tests; never a second scheduler.
            documents,stats=await news_collector(now,set())
            discovery={'statistics':stats,'selection':await discover_news(db,documents,stats,now)}
    except (SourceError,OSError,ValueError,StopRun) as exc:
        discovery={'reason':str(exc) if isinstance(exc,StopRun) else 'news_sources_unavailable'}
        web_state=run.report.get('web_research',{})
    if run.report.get('alternative_web_research'):
        context['alternative_web_research']=copy.deepcopy(run.report['alternative_web_research'])
    run.report=dict(run.report,editorial_version=2,news_discovery=discovery,candidate_attempts=previous_history)
    fetch_budget={'remaining':4}
    await db.commit()
    if _lane_engine is None:await discover_updates(db,now,fetch_budget,doc_loader)
    week=now.astimezone(MADRID).date()
    week_start=datetime.combine(week-timedelta(days=week.weekday()),datetime.min.time(),tzinfo=MADRID).astimezone(UTC)
    updates_weekly=await db.scalar(select(func.count(EditorialCandidate.id)).where(
        EditorialCandidate.state=='published',EditorialCandidate.target_article_id.is_not(None),
        EditorialCandidate.published_at>=week_start))
    publications=[]
    news_reason=('news_verification_exhausted' if discovery.get('web',{}).get('verification_status')=='no_verified_candidates'
                 else discovery.get('reason') or discovery.get('web',{}).get('reason') or 'no_viable_candidate')
    history=previous_history;last_reason=news_reason if _lane_engine=='news' else 'no_viable_candidate'
    engines=[(_lane_engine,2)] if _lane_engine else [('news',10),('evergreen',2)]
    for engine,max_paid in engines:
        if engine=='evergreen' and publications:break
        if engine=='evergreen':
            web=discovery.get('web',{})
            if not allow_evergreen:
                last_reason='news_only_no_verified_publication';break
            if _lane_engine is None and news_collector is collect and (discovery.get('reason') or web.get('research_status')=='invalid' or
                web.get('state') in {'calling','failed'} or
                (web.get('research_status')=='empty' and web.get('empty_reason')=='provider_did_not_explain_empty_result')):
                last_reason='research_failed_no_evergreen_substitution';break
            run.report=dict(run.report,fallback_decision={'reason':'news_unfunded' if web.get('state')=='unfunded' else 'no_verified_news_survived',
                'research_status':web.get('research_status'),'verified_candidates':web.get('verified_candidates',0)})
            context['fallback_decision']=copy.deepcopy(run.report['fallback_decision'])
            await db.commit()
        rows=(await db.scalars(select(EditorialCandidate).where(EditorialCandidate.engine==engine,
            EditorialCandidate.state.in_(PENDING),
            (EditorialCandidate.next_attempt_at.is_(None)) | (EditorialCandidate.next_attempt_at<=now))
            .order_by(case((EditorialCandidate.state.in_(['publication_error','correction_pending','budget_pending']),0),else_=1),
                EditorialCandidate.priority.desc(),EditorialCandidate.created_at).limit(20))).all()
        paid=sum(1 for item in history if item.get('engine')==engine and item.get('reserved_microusd',0)>0)
        candidate_ids=[row.id for row in rows]
        for candidate_id in candidate_ids:
            candidate=await db.get(EditorialCandidate,candidate_id,populate_existing=True)
            if paid>=max_paid:break
            if _lane_engine and candidate.target_article_id:continue  # Updates never fill a new-article quota.
            if candidate.target_article_id and updates_weekly>=1:
                candidate.state='deferred';candidate.reason='maintenance_weekly_cap';candidate.next_attempt_at=now+timedelta(hours=6)
                await db.commit();history.append({'candidate_id':candidate.id,'engine':engine,'reason':candidate.reason,'provider_calls':0})
                continue
            control=await db.get(ResearchControl,1,populate_existing=True)
            if not control or not control.enabled:raise StopRun('paused')
            if candidate.state=='publication_error':
                from app.research.recovery import recover_publication
                try:
                    valid=await recover_publication(db,candidate,config,redis,token,now,verifier,receipt_path)
                    if valid:
                        publications.append({'candidate_id':candidate.id,'article_id':candidate.article_id,
                            'url':candidate.details['verification']['url'],'reserved_microusd':0,'recovered':True})
                        run.article_id=candidate.article_id
                        run.status='published';run.reason='quality_checks_passed'
                        run.report=dict(run.report,publications=publications)
                        if _lane_engine:run.candidate_id=candidate.id
                        await db.commit();return
                except StopRun as exc:
                    candidate.state='technical_error';candidate.reason=str(exc)
                    candidate.details=dict(candidate.details,failure={'code':str(exc),'details':exc.details})
                    await db.commit()
                history.append({'candidate_id':candidate.id,'engine':engine,'reason':candidate.reason,'provider_calls':0})
                continue
            correction=bool(candidate.details.get('resume_report',{}).get('resume_correction'))
            candidate.state='preparing';await db.commit()
            saved=candidate.details.get('resume_report')
            resume=bool(saved and ((candidate.article_id and (saved.get('pending_review') or (saved.get('review') or {}).get('approved'))) or (correction and saved.get('proposal'))))
            replaying=bool(_lane_engine and saved and saved.get('stage_checkpoints'))
            try:
                kwargs={'receipt_path':receipt_path,'practical_slots':config.practical_publications}
                if doc_loader:kwargs['doc_loader']=doc_loader
                if resume:
                    from app.research.executions import resume_material
                    evidence,policy,saved,_=await resume_material(db,candidate,now,receipt_path,allow_draftless=not candidate.article_id,doc_loader=doc_loader)
                elif replaying:
                    from app.research.executions import resume_material
                    evidence,policy,saved,_=await resume_material(db,candidate,now,receipt_path,allow_draftless=True,doc_loader=doc_loader)
                else:evidence,policy=await prepare_candidate(db,candidate,now,fetch_budget,**kwargs)
            except (SourceError,StopRun) as exc:
                reason=exc.code if isinstance(exc,SourceError) else str(exc)
                candidate.details=dict(candidate.details,last_preflight_error={'code':reason,'http_status':getattr(exc,'http_status',None),'details':getattr(exc,'details',[])})
                await defer_or_reject(db,candidate,reason,now)
                history.append({'candidate_id':candidate.id,'engine':engine,'reason':reason,'provider_calls':0})
                last_reason=reason
                if reason=='document_fetch_budget':break
                continue
            policy['internal_links']=policy.get('internal_links') or [('Más guías de '+candidate.section,'/'+candidate.section)]
            related=(await db.scalars(select(Article).where(Article.status=='published').order_by(Article.published_at.desc()).limit(60))).all()
            words=topic_words(candidate.keyword+' '+candidate.topic)
            linked=0
            for article in related:
                if linked>=4:break
                if not resume and not replaying and len(words & topic_words(article.title))>=(2 if article.section!=candidate.section else 1) and article.id!=candidate.target_article_id:
                    policy['internal_links'].append((article.title,'/articulos/'+article.slug));linked+=1
            saved=candidate.details.get('resume_report')
            resume=bool(saved and ((candidate.article_id and (saved.get('pending_review') or (saved.get('review') or {}).get('approved'))) or (correction and saved.get('proposal'))))
            run.article_id=candidate.article_id if resume else None
            if _lane_engine:run.candidate_id=candidate.id
            run.report=dict(saved or {},**context,web_research=web_state,publications=publications,editorial_version=2,news_discovery=discovery,candidate_attempts=history,
                active_candidate_id=candidate.id,engine=engine,policy={k:v for k,v in policy.items() if k!='example'})
            candidate.state='generating'
            if not resume and not replaying:candidate.attempts+=1
            paid+=1
            await db.commit()
            before=run.reserved_microusd
            sink_token=USAGE_SINK.set(lambda c,s,u:usage_sink(db,run,candidate,c,s,u))
            try:
                async def collector(stamp,urls):return evidence,{'candidate_count':len(evidence),'fetch_failures':0}
                await worker.pipeline(db,run,config,redis,token,collector,generator,resume='correction' if resume and correction else 'review' if resume else False,policy=policy,candidate=candidate)
                if candidate.state=='needs_verification':
                    candidate.details=dict(candidate.details,editorial_record=copy.deepcopy(run.report),resume_report=copy.deepcopy(run.report))
                    await db.commit()
                    valid=await verify_candidate(db,candidate,verifier,utcnow())
                    run.reason='quality_checks_passed' if valid else 'publication_verification_pending' if candidate.state=='needs_verification' else candidate.reason
                    if candidate.state not in {'published','needs_verification'}:run.status='skipped'
                    run.report=dict(run.report,verification=candidate.details.get('verification') or {'reason':candidate.reason})
                    run.finished_at=utcnow();await db.commit()
                    if candidate.state=='needs_verification':
                        if _lane_engine:run.status='needs_verification';await db.commit()
                        return
                    if candidate.state=='published':
                        publications.append({'candidate_id':candidate.id,'article_id':candidate.article_id,
                            'url':candidate.details.get('verification',{}).get('url'),
                            'reserved_microusd':run.reserved_microusd-before})
                        history.append({'candidate_id':candidate.id,'engine':engine,'reason':'quality_checks_passed',
                            'reserved_microusd':run.reserved_microusd-before})
                        run.report=dict(run.report,publications=publications,candidate_attempts=history)
                        await db.commit()
                        if engine=='evergreen' or (max_publications is not None and len(publications)>=max_publications):return
                        continue
                elif candidate.state=='ready':return  # Explicit auto_publish=false.
                reason=candidate.reason or 'publication_check_failed'
            except Exception as exc:
                await db.rollback()
                if _lane_engine:
                    from app.research.lanes import LaneRun
                    run=LaneRun(await db.get(EditorialLaneRun,lane_id,populate_existing=True),
                        await db.get(ResearchRun,run_id,populate_existing=True))
                else:run=await db.get(ResearchRun,run_id,populate_existing=True)
                candidate=await db.get(EditorialCandidate,candidate_id,populate_existing=True)
                reason=str(exc) if isinstance(exc,StopRun) else 'candidate_internal_error'
                run.report=dict(run.report,failure={'code':reason,'details':exc.details if isinstance(exc,StopRun) else []})
                candidate.article_id=run.article_id
                preserve(candidate,run.report,reason,exc.details if isinstance(exc,StopRun) else [])
                if reason=='budget_exhausted' and run.reserved_microusd==before and not resume:
                    candidate.attempts=max(0,candidate.attempts-1)
                await defer_or_reject(db,candidate,reason,now)
                if _lane_engine and any(c.get('state') in {'calling','uncertain','reserving'} for c in run.report.get('stage_checkpoints',{}).values()):
                    candidate.state='technical_error';candidate.reason='uncertain_provider_result'
                    candidate.details=dict(candidate.details,uncertain_checkpoint=copy.deepcopy(run.report))
                    await db.commit()
            finally:USAGE_SINK.reset(sink_token)
            workspace={k:v for k,v in run.report.items() if k not in {'candidate_attempts','news_discovery'}}
            history.append({'candidate_id':candidate.id,'engine':engine,'reason':reason,
                'reserved_microusd':run.reserved_microusd-before,'report':workspace})
            last_reason=reason
            if reason=='budget_exhausted' and run.reserved_microusd==before and not run.article_id:
                continue  # Another shorter candidate may fit; no provider call was made.
            if reason in {'provider_unavailable','incomplete_generation','budget_exhausted','paused','lock_lost','usage_outside_budget_bound','uncertain_provider_result'}:
                run.status='published' if publications else 'draft' if run.article_id else 'skipped';run.reason=reason;run.finished_at=utcnow()
                run.report=dict(run.report,candidate_attempts=history);await db.commit();return
    run.status='published' if publications else 'skipped';run.reason='quality_checks_passed' if publications else last_reason;run.finished_at=utcnow()
    run.report={**context,'web_research':web_state,'publications':publications,'editorial_version':2,'news_discovery':discovery,'candidate_attempts':history};run.article_id=publications[-1]['article_id'] if publications else None
    await db.commit()


async def reconcile_publications(verifier=None):
    """Resume only read-only verification after restart; never repeat a paid request."""
    import secrets
    from app.core.db import get_sessionmaker
    from app.core.limits import get_redis
    from app.research.worker import LOCK,RELEASE
    redis=get_redis();token=secrets.token_hex(24).encode()
    if not await redis.set(LOCK,token,nx=True,ex=1800):return
    try:
        async with get_sessionmaker()() as db:
            rows=(await db.scalars(select(EditorialCandidate).where(EditorialCandidate.state=='needs_verification',
                (EditorialCandidate.next_attempt_at.is_(None)) | (EditorialCandidate.next_attempt_at<=utcnow())).limit(3))).all()
            ids=[c.id for c in rows]
            for cid in ids:
                candidate=await db.get(EditorialCandidate,cid,populate_existing=True)
                await verify_candidate(db,candidate,verifier=verifier)
                lane=await db.scalar(select(EditorialLaneRun).where(EditorialLaneRun.article_id==candidate.article_id).order_by(EditorialLaneRun.id.desc()).limit(1))
                if lane:
                    lane.status='published' if candidate.state=='published' else 'needs_verification' if candidate.state=='needs_verification' else 'skipped'
                    lane.reason='quality_checks_passed' if candidate.state=='published' else 'publication_verification_pending' if candidate.state=='needs_verification' else candidate.reason
                    if candidate.state=='published' and not lane.report.get('publications'):
                        lane.report=dict(lane.report,publications=[{'candidate_id':candidate.id,'article_id':candidate.article_id,
                            'url':candidate.details['verification']['url']}])
                    await db.commit()
                    from app.research.lanes import summarize
                    parent=await db.get(ResearchRun,lane.run_id)
                    await summarize(db,parent)
                    continue
                run=await db.scalar(select(ResearchRun).where(ResearchRun.article_id==candidate.article_id).order_by(ResearchRun.id.desc()).limit(1))
                if run:
                    run.status='published' if candidate.state in {'published','needs_verification'} else 'skipped'
                    run.reason='quality_checks_passed' if candidate.state=='published' else 'publication_verification_pending' if candidate.state=='needs_verification' else candidate.reason
                    run.report=dict(run.report,verification=candidate.details.get('verification') or {'reason':candidate.reason})
                    await db.commit()
    finally:await redis.eval(RELEASE,1,LOCK,token)
