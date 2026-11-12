"""Durable quoted manual jobs; the existing worker executes only confirmed jobs."""
import asyncio,copy,hashlib,json,secrets
from datetime import UTC,datetime,timedelta
from sqlalchemy import select,func
from app.models import Article,EditorialCandidate,EditorialExecution,ResearchRun,ResearchControl,AuditLog,utcnow
from app.core.db import get_sessionmaker
from app.core.limits import get_redis
from app.research.config import settings,MADRID
from app.research.documents import aware
from app.research.evidence import catalogue,index
from app.research.writing import Draft,Review,VOICE,REVIEW_INSTRUCTIONS,REVIEW_MAX_OUTPUT_TOKENS,prepare_request,validate_draft,Citation,StopRun,USAGE_SINK
from app.research.publication import article_snapshot,verify_candidate
from app.research.sources import SourceError

ACTIVE=['preparing','awaiting_approval','queued','running']


def digest(data):return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()


def prices(config):return {k:str(getattr(config,k)) for k in ['model','daily_usd','monthly_usd','input_per_million','output_per_million']}


async def allowance(db,config,day):
    daily=await db.scalar(select(func.coalesce(func.sum(ResearchRun.reserved_microusd),0)).where(ResearchRun.editorial_date==day))
    monthly=await db.scalar(select(func.coalesce(func.sum(ResearchRun.reserved_microusd),0)).where(ResearchRun.editorial_date>=day.replace(day=1)))
    return max(0,min(int(config.daily_usd*1000000)-daily,int(config.monthly_usd*1000000)-monthly))


class Context:
    def __init__(self,execution,budget):object.__setattr__(self,'execution',execution);object.__setattr__(self,'budget_run',budget)
    @property
    def id(self):return self.budget_run.id
    @property
    def editorial_date(self):return self.budget_run.editorial_date
    @property
    def expected_request_hash(self):return self.execution.prepared['first_hash']
    def __getattr__(self,key):return getattr(self.execution,key)
    def __setattr__(self,key,value):setattr(self.execution,key,value)


async def resume_material(db,candidate,now,receipt_path=None,allow_draftless=False,allow_archived=False,doc_loader=None):
    from app.research.examples import verified_example
    from app.research.blueprints import BY_KEY
    import os
    saved=copy.deepcopy(candidate.details.get('resume_report') or {})
    sources=saved['evidence_catalogue'];index(sources)
    limit=timedelta(hours=48 if candidate.engine=='news' else 72)
    stale=any(not -timedelta(minutes=5)<=now-aware(datetime.fromisoformat(s['retrieved_at']))<=limit for s in sources)
    revalidated=candidate.details.get('source_revalidated_at')
    recent=revalidated and timedelta(0)<=now-aware(datetime.fromisoformat(revalidated))<=limit
    if stale and not recent:
        if candidate.engine!='evergreen':raise StopRun('checkpoint_sources_stale')
        from app.research.documents import official_document
        from app.research.queue import example_focused,focused_document
        fetch={'remaining':4}
        for source in sources:
            fresh=await (doc_loader or official_document)(db,source.get('raw_document_url',source['url']),now,fetch)
            focus=candidate.details.get('focus')
            fresh=focused_document(fresh,focus['key']) if focus else example_focused(fresh,source.get('focus_terms',[]))
            if catalogue([fresh])[0]['content_sha256']!=source['content_sha256']:
                raise StopRun('evidence_source_changed')
        # Keep the exact old fragment IDs, request hashes, and source bytes.
        # The new independent retrieval is recorded without rewriting history.
        candidate.details=dict(candidate.details,source_revalidated_at=now.isoformat())
        await db.commit()
    policy=copy.deepcopy(saved['policy'])
    blueprint=BY_KEY.get(candidate.details.get('blueprint'))
    if blueprint and blueprint.example:
        example=verified_example(blueprint.example,receipt_path or os.environ.get('EDITORIAL_EXAMPLE_RECEIPT','/app/receipts/verified-examples.json'),now)
        if not example:raise StopRun('example_not_verified')
        policy['example']=example
    article=await db.get(Article,candidate.article_id) if candidate.article_id else None
    if not candidate.article_id and allow_draftless and (saved.get('resume_correction') and saved.get('proposal') or any(e.get('state')=='response' for e in saved.get('stage_checkpoints',{}).values())):
        return sources,policy,saved,None
    if not article or article.status not in (('draft','archived') if allow_archived else ('draft',)):raise StopRun('article_changed')
    proposal=Draft.model_validate(saved.get('evidence') if saved.get('resume_correction') and saved.get('evidence') else saved['proposal'])
    expected=validate_draft(proposal,sources,[],policy,metadata_refs=[Citation.model_validate(r) for r in saved.get('reviewed_metadata_evidence',[])],provisional=not saved.get('citations_bound_by_review')).model_dump(mode='json')
    if any(getattr(article,k)!=v for k,v in expected.items()):raise StopRun('article_changed')
    if not saved.get('pending_review') and not saved.get('resume_correction'):
        # A known approved review can be replayed after a deterministic validator
        # fix. Recheck all evidence and text; never manufacture an approval or
        # retry an uncertain/paid correction to get past a failed validation.
        from app.research.writing import GroundedReview,bind_reviewed_evidence
        entries=saved.get('stage_checkpoints',{})
        if any(v.get('state') in {'reserving','calling','uncertain'} for v in entries.values()):raise StopRun('uncertain_provider_result')
        if not any(v.get('stage')=='Review' and v.get('state')=='response' for v in entries.values()):raise StopRun('missing_review_checkpoint')
        verdict=GroundedReview.model_validate(saved.get('review') or {})
        bound,metadata=bind_reviewed_evidence(proposal,verdict,sources,policy)
        existing=(await db.scalars(select(Article).where(Article.status=='published',Article.id!=article.id).limit(300))).all()
        validate_draft(bound,sources,existing,policy,metadata_refs=metadata)
        saved=dict(saved,pending_review=True,replaying_verified_review=True)
    return sources,policy,saved,article


async def prepare_job(db,job,config,now=None,doc_loader=None,receipt_path=None):
    from app.research.queue import seed_evergreen,prepare_candidate,discover_news
    from app.research.examples import verified_example
    from app.research.blueprints import BY_KEY
    now=now or utcnow();day=now.astimezone(MADRID).date()
    permit=job.prepared.get('backlog_authorization_id')
    await seed_evergreen(db)
    if not job.candidate_id:
        resumable=await db.scalar(select(EditorialCandidate).where(EditorialCandidate.article_id.is_not(None),EditorialCandidate.state.in_(['deferred','ready'])).order_by(EditorialCandidate.priority.desc()).limit(1))
        if resumable and resumable.details.get('resume_report',{}).get('pending_review'):job.candidate_id=resumable.id
    if job.mode=='auto' and not job.candidate_id:
        from app.research.sources import collect,recover_related
        from app.research.selection import select as choose
        docs,stats=await collect(now,set(),initial_document_limit=6)
        if not choose(docs)[0]:docs,stats=await recover_related(docs,stats)
        await discover_news(db,docs,stats,now)
        job.report=dict(job.report,discovery=stats)
        rows=(await db.scalars(select(EditorialCandidate).where(EditorialCandidate.state.in_(['queued','ready','deferred']),
            (EditorialCandidate.next_attempt_at.is_(None))|(EditorialCandidate.next_attempt_at<=now)).order_by(EditorialCandidate.priority.desc()).limit(8))).all()
    else:rows=[await db.get(EditorialCandidate,job.candidate_id)] if job.candidate_id else []
    fetch_budget={'remaining':4};last='no_viable_candidate'
    for candidate in rows:
        if not candidate or candidate.state in {'published','generating','needs_verification','rejected'}:continue
        saved=copy.deepcopy(candidate.details.get('resume_report') or {})
        resume=bool(candidate.article_id and (saved.get('pending_review') or (saved.get('review') or {}).get('approved')))
        correction=job.mode=='correction'
        if job.mode=='resume' and not resume:continue
        try:
            if correction:
                from app.research.examples import verified_example
                from app.research.draft_recovery import saved_draft_matches
                from app.research.quality import resume_feedback
                from app.research.style import correction_plan
                import os
                old_policy=copy.deepcopy(saved.get('policy') or {})
                blueprint=BY_KEY.get(candidate.details.get('blueprint'))
                if not saved.get('proposal') or not candidate.article_id or int(saved.get('corrections_used',0))>=2:raise StopRun('correction_limit_reached')
                if any(e.get('state') in {'reserving','calling','uncertain'} for e in saved.get('stage_checkpoints',{}).values()):raise StopRun('uncertain_provider_result')
                article=await db.get(Article,candidate.article_id,populate_existing=True)
                if blueprint and blueprint.example:
                    old_policy['example']=verified_example(blueprint.example,receipt_path or os.environ.get('EDITORIAL_EXAMPLE_RECEIPT','/app/receipts/verified-examples.json'),now)
                    if not old_policy['example']:raise StopRun('example_not_verified')
                if not article or article.status!='draft' or not saved_draft_matches(article,saved,old_policy):raise StopRun('article_changed')
                snapshot=article_snapshot(article)
                kwargs={'receipt_path':receipt_path,'practical_slots':config.practical_publications}
                if doc_loader:kwargs['doc_loader']=doc_loader
                sources,policy=await prepare_candidate(db,candidate,now,fetch_budget,**kwargs)
                policy['internal_links']=old_policy.get('internal_links') or [('Más guías de '+candidate.section,'/'+candidate.section)]
                await db.refresh(article)
                if article_snapshot(article)!=snapshot:raise StopRun('article_changed')
                proposal=Draft.model_validate(saved['proposal'])
                feedback=resume_feedback(saved);feedback=dict(feedback,editing_plan=correction_plan(proposal,feedback))
                from app.research.writing import CORRECT_INSTRUCTIONS,evidence_context
                data={'draft':proposal.model_dump(),'errors':feedback,'sources':evidence_context(proposal,catalogue(sources)),'editorial_policy':policy}
                first_schema,instructions,first_config=Draft,CORRECT_INSTRUCTIONS,config.model_copy(update={'max_output_tokens':REVIEW_MAX_OUTPUT_TOKENS})
                saved=dict(saved,resume_correction=True,recovery_correction_limit=2)
                resume=True
            elif resume:
                sources,policy,saved,article=await resume_material(db,candidate,now,receipt_path)
                proposal=Draft.model_validate(saved['proposal'])
                from app.research.quality import complete_summary
                proposal.summary=complete_summary(proposal.summary)
                snapshot=article_snapshot(article)
                data={'draft':proposal.model_dump(),'sources':catalogue(sources),'editorial_policy':policy}
                first_schema,instructions,first_config=Review,REVIEW_INSTRUCTIONS,config.model_copy(update={'max_output_tokens':REVIEW_MAX_OUTPUT_TOKENS})
            else:
                kwargs={'receipt_path':receipt_path,'practical_slots':config.practical_publications}
                if doc_loader:kwargs['doc_loader']=doc_loader
                sources,policy=await prepare_candidate(db,candidate,now,fetch_budget,**kwargs)
                policy['internal_links']=[('Más guías de '+candidate.section,'/'+candidate.section)]
                existing=(await db.scalars(select(Article).order_by(Article.id.desc()).limit(300))).all()
                data={'sources':catalogue(sources),'recent_titles':[a.title for a in existing[:80]],'editorial_policy':policy}
                snapshot=None;first_schema,instructions,first_config=Draft,VOICE,config
            # Freeze generated retrieval metadata once, before quotation and persistence.
            sources=catalogue(sources);data['sources']=sources
            request=prepare_request(first_config,first_schema,instructions,data)
            request_hash=digest(request[2]);cost=request[-1]
            cache=saved.get('stage_checkpoints',{}).get(request_hash,{})
            if cache.get('state') in {'reserving','calling','uncertain'}:raise StopRun('uncertain_provider_result')
            from app.research.checkpoints import retryable_incomplete
            if cache.get('state')=='failed' and not retryable_incomplete(cache,day):raise StopRun(cache['reason'],cache.get('details'))
            already_approved=resume and saved.get('approved_checkpoint')==digest({'draft':proposal.model_dump(mode='json'),'catalogue':catalogue(sources),'metadata':saved.get('reviewed_metadata_evidence',[])})
            maximum=0 if cache.get('state')=='response' or already_approved else cost if resume and not correction else min(150000,await allowance(db,config,day))
            if cost>await allowance(db,config,day) and maximum:raise StopRun('budget_exhausted')
            expires=min(now+timedelta(minutes=30),datetime.combine(day+timedelta(days=1),datetime.min.time(),tzinfo=MADRID).astimezone(UTC))
            prepared={'sources':sources,'policy':policy,'resume_report':saved if resume else {},'snapshot':snapshot,
                'recent_titles':data.get('recent_titles'),
                'first_hash':request_hash,'first_stage':'correction' if correction else 'review' if resume else 'draft','max_calls':1 if resume and not correction else 4,
                'prices':prices(config),'day':str(day),'expires_at':expires.isoformat(),'max_reserved_microusd':maximum}
            if permit:prepared['backlog_authorization_id']=permit
            prepared['quote_digest']=digest(prepared)
            job.prepared=prepared;job.candidate_id=candidate.id;job.article_id=candidate.article_id if resume else None
            job.max_reserved_microusd=maximum;job.expires_at=expires;job.state='awaiting_approval';job.reason=''
            job.report=dict(job.report,current_stage='awaiting_approval',preflight={'sources':len(sources),'resume':resume,'provider_calls':0})
            await db.commit();return
        except (StopRun,SourceError) as exc:last=str(exc) if isinstance(exc,StopRun) else exc.code
    job.state='failed';job.reason=last;job.finished_at=now;await db.commit()


async def execute_job(db,job,config,redis,token,generator=None,verifier=None):
    from app.research import worker
    from app.research.editorial import usage_sink
    from app.research.writing import generate
    candidate=await db.get(EditorialCandidate,job.candidate_id)
    if candidate.state=='published':job.state='completed';job.reason='already_published';await db.commit();return
    if candidate.state=='needs_verification':
        await finish_verification(db,job,candidate,verifier);return
    if prices(config)!=job.prepared['prices']:raise StopRun('quote_changed')
    day=utcnow().astimezone(MADRID).date()
    if str(day)!=job.prepared['day'] or (not job.started_at and aware(job.expires_at)<utcnow()):raise StopRun('quote_expired')
    control=await db.scalar(select(ResearchControl).where(ResearchControl.id==1).with_for_update())
    if not control or not control.enabled:raise StopRun('paused')
    if job.mode=='rapid' and not control.rapid_enabled:raise StopRun('rapid_disabled')
    start=datetime.combine(day,datetime.min.time(),tzinfo=MADRID).astimezone(UTC)
    if config.two_lanes:
        from app.research.quota import check_quota
        await check_quota(db,config,candidate,utcnow(),job)
    elif await db.scalar(select(EditorialCandidate.id).where(EditorialCandidate.state=='published',EditorialCandidate.published_at>=start).limit(1)):raise StopRun('daily_publication_limit')
    week=start-timedelta(days=day.weekday())
    if not config.two_lanes and (await db.scalar(select(func.count(EditorialCandidate.id)).where(EditorialCandidate.state=='published',EditorialCandidate.published_at>=week)))>=5:raise StopRun('weekly_publication_limit')
    bucket=await db.scalar(select(ResearchRun).where(ResearchRun.editorial_date==day))
    if not bucket:
        bucket=ResearchRun(editorial_date=day,status='skipped',reason='manual_budget_bucket',finished_at=utcnow(),report={'budget_bucket':True})
        db.add(bucket);await db.flush()
    job.run_id=bucket.id
    snapshot=job.prepared.get('snapshot')
    recovering_review=bool(job.started_at and job.article_id and job.report.get('pending_review'))
    if recovering_review and not snapshot:
        article=await db.get(Article,job.article_id,populate_existing=True)
        saved_draft=Draft.model_validate(job.report['proposal'])
        expected=validate_draft(saved_draft,job.prepared['sources'],[],job.prepared['policy'],metadata_refs=[Citation.model_validate(r) for r in job.report.get('reviewed_metadata_evidence',[])],provisional=not job.report.get('citations_bound_by_review')).model_dump(mode='json')
        if not article or article.status!='draft' or any(getattr(article,k)!=v for k,v in expected.items()):raise StopRun('article_changed')
        snapshot=article_snapshot(article)
    if snapshot:
        article=await db.get(Article,job.article_id,populate_existing=True)
        current=job.report if job.started_at else {}
        if current.get('approved_checkpoint'):
            approved=Draft.model_validate(current['proposal'])
            if current['approved_checkpoint']!=digest({'draft':approved.model_dump(mode='json'),'catalogue':catalogue(job.prepared['sources']),'metadata':current.get('reviewed_metadata_evidence',[])}):raise StopRun('article_changed')
            expected=validate_draft(approved,job.prepared['sources'],[],job.prepared['policy'],metadata_refs=[Citation.model_validate(r) for r in current.get('reviewed_metadata_evidence',[])]).model_dump(mode='json')
            if not article or article.status!='draft' or any(getattr(article,k)!=v for k,v in expected.items()):raise StopRun('article_changed')
        elif not article or article_snapshot(article)!=snapshot:raise StopRun('article_changed')
    old_report=copy.deepcopy(job.report if job.started_at else job.prepared.get('resume_report') or {})
    old_report['policy']={k:v for k,v in job.prepared['policy'].items() if k!='example'}
    existing_cache=job.report.get('stage_checkpoints',{})
    job.report=dict(old_report,current_stage='review' if snapshot else 'draft',stage_checkpoints=existing_cache or old_report.get('stage_checkpoints',{}),reserved_calls=job.report.get('reserved_calls',0),manual_request_started=job.report.get('manual_request_started',False))
    if job.prepared.get('recent_titles') is not None:job.report=dict(job.report,generation_recent_titles=job.prepared['recent_titles'])
    if not snapshot and not job.started_at:candidate.attempts+=1
    job.state='running';job.started_at=job.started_at or utcnow();candidate.state='generating'
    await db.commit()
    context=Context(job,bucket)
    sink=USAGE_SINK.set(lambda c,s,u:usage_sink(db,context,candidate,c,s,u))
    try:
        async def collector(now,urls):return job.prepared['sources'],{'candidate_count':len(job.prepared['sources']),'fetch_failures':0}
        await worker.pipeline(db,context,config,redis,token,collector,generator or generate,resume='correction' if job.prepared.get('first_stage')=='correction' else 'review' if snapshot else False,
            policy=job.prepared['policy'],candidate=candidate)
        candidate.details=dict(candidate.details,editorial_record=copy.deepcopy(job.report))
        await db.commit();await finish_verification(db,job,candidate,verifier)
    finally:USAGE_SINK.reset(sink)


async def finish_verification(db,job,candidate,verifier=None):
    passed=await verify_candidate(db,candidate,verifier)
    job.article_id=candidate.article_id
    job.report=dict(job.report,verification=candidate.details.get('verification'),current_stage='published' if passed else 'verification')
    if passed:job.state='completed';job.reason='quality_checks_passed';job.finished_at=job.finished_at or utcnow()
    elif candidate.state!='needs_verification':job.state='failed';job.reason=candidate.reason;job.finished_at=utcnow()
    else:job.state='running';job.reason='publication_verification_pending'
    if passed and job.run_id:
        # The recovered article can belong to yesterday's research while today's
        # budget pays only the remaining review. Reconcile the original history,
        # without moving costs between days or changing the publication date.
        buckets=(await db.scalars(select(ResearchRun).where(ResearchRun.status=='draft',
            ResearchRun.article_id==job.article_id,
            ResearchRun.report['active_candidate_id'].as_integer()==candidate.id).limit(10))).all()
        for bucket in buckets:
            bucket.status='published';bucket.reason='quality_checks_passed';bucket.finished_at=utcnow()
            bucket.report=dict(bucket.report,recovered_by_execution=job.id,current_stage='published',pending_review=False,
                recovery_budget_run_id=job.run_id,
                recovery_previous_proposal=bucket.report.get('proposal'),
                **{k:job.report[k] for k in ['proposal','evidence','reviewed_metadata_evidence','citations_bound_by_review','approved_checkpoint'] if k in job.report},
                review=job.report.get('review'),verification=job.report.get('verification'),
                publications=[*bucket.report.get('publications',[]),{'candidate_id':candidate.id,'article_id':job.article_id,
                    'execution_id':job.id,'url':(job.report.get('verification') or {}).get('url')}])
            db.add(AuditLog(actor='automation',action='research_recovery_verified',entity_type='research',entity_id=bucket.id,
                details={'execution_id':job.id,'article_id':job.article_id,'budget_run_id':job.run_id,'budgets_unchanged':True}))
    if passed and job.run_id:
        funding=await db.scalar(select(ResearchRun).where(ResearchRun.id==job.run_id).with_for_update())
        if funding:
            report=dict(funding.report)
            report.setdefault('nightly_result_before_manual',{'status':funding.status,'reason':funding.reason})
            manual=list(report.get('manual_publications',[]))
            item={'candidate_id':candidate.id,'article_id':job.article_id,'execution_id':job.id,
                  'url':(job.report.get('verification') or {}).get('url')}
            if not any(p.get('article_id')==job.article_id for p in manual):manual.append(item)
            publications=list(report.get('publications',[]))
            if not any(p.get('article_id')==job.article_id for p in publications):publications.append(item)
            funding.report=dict(report,manual_publications=manual,publications=publications)
            funding.status='published'
            if funding.reason!='quality_checks_passed':funding.reason='partial_publication'
    await db.commit()
    if passed:await settle_execution(db,job)


async def settle_execution(db,job):
    """Release only a finished execution's fully reported unused reserve."""
    from app.models import GenerationUsage
    await db.scalar(select(ResearchControl).where(ResearchControl.id==1).with_for_update())
    job=await db.scalar(select(EditorialExecution).where(EditorialExecution.id==job.id).with_for_update().execution_options(populate_existing=True))
    if job.state not in {'completed','failed'} or job.report.get('reservation_settled'):
        await db.commit();return
    entries=[e for e in job.report.get('stage_checkpoints',{}).values() if e.get('execution_id')==job.id]
    if len(entries)!=job.report.get('reserved_calls',0) or not entries:
        await db.commit();return
    cost=maximum=0
    for e in entries:
        usage=e.get('usage',{})
        ledger=await db.scalar(select(GenerationUsage).where(GenerationUsage.request_key==e.get('ledger_key')))
        if (e.get('state')!='response' or not ledger or ledger.run_id!=job.run_id or ledger.stage!=e.get('stage')
            or ledger.input_tokens!=usage.get('input_tokens') or ledger.output_tokens!=usage.get('output_tokens')
            or not 0<=ledger.estimated_microusd<=e.get('maximum_microusd',-1)):
            await db.commit();return
        cost+=ledger.estimated_microusd;maximum+=e['maximum_microusd']
    if maximum!=job.reserved_microusd:
        await db.commit();return
    bucket=await db.get(ResearchRun,job.run_id,populate_existing=True)
    released=maximum-cost
    if not bucket or released>bucket.reserved_microusd:raise StopRun('reservation_accounting_mismatch')
    bucket.reserved_microusd-=released;job.reserved_microusd=cost
    job.report=dict(job.report,reservation_settled={'maximum_microusd':maximum,'reported_microusd':cost,'released_microusd':released,'billing_verified':False})
    db.add(AuditLog(actor='automation',action='execution_reservation_settled',entity_type='research_execution',entity_id=job.id,details=job.report['reservation_settled']))
    await db.commit()


async def process_next():
    from app.research.worker import LOCK,RELEASE
    redis=get_redis();token=secrets.token_hex(24).encode()
    if not await redis.set(LOCK,token,nx=True,ex=1800):return
    try:
        async with get_sessionmaker()() as db:
            job=await db.scalar(select(EditorialExecution).where((EditorialExecution.state.in_(['preparing','queued','running']))|
                ((EditorialExecution.mode=='rapid')&(EditorialExecution.state=='awaiting_approval'))).order_by(EditorialExecution.id).limit(1))
            if not job:return
            jid=job.id
            try:
                if job.state in {'preparing','awaiting_approval'}:
                    if job.state=='preparing':await asyncio.wait_for(prepare_job(db,job,settings()),900)
                    if job.mode=='rapid' and job.state=='awaiting_approval':
                        from app.research.rapid import confirm_job
                        await confirm_job(db,job)
                else:
                    if job.state=='running' and job.reason!='publication_verification_pending':
                        cache=job.report.get('stage_checkpoints',{})
                        if any(v.get('state') in {'reserving','calling','uncertain'} for v in cache.values()):raise StopRun('uncertain_provider_result')
                        if job.report.get('reserved_calls',0)>len(cache):raise StopRun('uncertain_provider_result')
                    candidate=await db.get(EditorialCandidate,job.candidate_id)
                    if candidate and candidate.state=='needs_verification' and candidate.next_attempt_at and aware(candidate.next_attempt_at)>utcnow():return
                    await asyncio.wait_for(execute_job(db,job,settings(),redis,token),900)
            except Exception as exc:
                await db.rollback();job=await db.get(EditorialExecution,jid,populate_existing=True)
                reason=str(exc) if isinstance(exc,StopRun) else 'execution_internal_error'
                job.state='uncertain' if reason=='uncertain_provider_result' else 'expired' if reason=='quote_expired' else 'failed'
                job.reason=reason;job.finished_at=utcnow()
                print(json.dumps({'event':'manual_execution_finished','execution_id':jid,'state':job.state,'reason':reason,'exception_type':type(exc).__name__}),flush=True)
                if job.candidate_id:
                    candidate=await db.get(EditorialCandidate,job.candidate_id)
                    if candidate.state=='generating':
                        budget_failure=reason in {'budget_exhausted','execution_budget_exhausted','execution_call_limit'}
                        candidate.state='deferred' if job.report.get('pending_review') or budget_failure else 'rejected';candidate.reason=reason
                        if budget_failure and not job.reserved_microusd:candidate.attempts=max(0,candidate.attempts-1)
                        if budget_failure:candidate.next_attempt_at=utcnow()+timedelta(hours=6)
                        candidate.article_id=job.article_id
                        candidate.details=dict(candidate.details,resume_report=copy.deepcopy(job.report))
                await db.commit()
                if job.state=='failed':await settle_execution(db,job)
    finally:await redis.eval(RELEASE,1,LOCK,token)
