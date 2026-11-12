"""Durable execution and recovery; provider substituted, disposable database only."""
import asyncio,copy,json
from datetime import timedelta
import pytest
from sqlalchemy import select
from test_research import client,database,EVIDENCE,Redis
from test_articles_api import AUTH
from test_evidence_first import grounded,approved_payload
from app.models import ResearchControl,ResearchRun,EditorialCandidate,EditorialExecution,Article,utcnow
from app.research import writing,evidence,worker,executions
from app.research.config import ResearchSettings,MADRID


def test_execution_api_permissions_and_idempotency(client,monkeypatch):
    async def limit(*a):pass
    monkeypatch.setattr('app.core.limits.limit',limit)
    async def seed(db):db.add(ResearchControl(id=1,enabled=False))
    database(seed)
    body={'mode':'auto','request_key':'repeatable-request-1234'}
    assert client.post('/editorial/research/executions',json=body).status_code==401
    one=client.post('/editorial/research/executions',headers=AUTH,json=body)
    assert one.status_code==200
    two=client.post('/editorial/research/executions',headers=AUTH,json=body)
    assert two.json()['id']==one.json()['id']
    body['request_key']='another-request-key-1234'
    assert client.post('/editorial/research/executions',headers=AUTH,json=body).status_code==409
    assert client.get('/editorial/research',headers=AUTH).json()['executions'][0]['state']=='preparing'


def test_saved_response_replays_without_reserving_or_calling(client,monkeypatch):
    calls=[];reserves=[]
    corpus=evidence.catalogue(EVIDENCE)
    def provider(config,payload):calls.append(payload);return grounded(corpus).model_dump_json(),{'input_tokens':10,'output_tokens':100}
    monkeypatch.setattr(writing,'call',provider)
    async def operation(db):
        row=ResearchRun(editorial_date=utcnow().date());db.add(row);await db.commit()
        from app.research.checkpoints import store_for
        token=writing.CHECKPOINT_STORE.set(store_for(db,row))
        async def reserve(cost):reserves.append(cost)
        try:
            first=await writing.generate(ResearchSettings(),writing.Draft,writing.VOICE,{'sources':corpus},reserve)
            second=await writing.generate(ResearchSettings(),writing.Draft,writing.VOICE,{'sources':corpus},reserve)
            assert first==second and len(calls)==len(reserves)==1
            entry=next(iter(row.report['stage_checkpoints'].values()));entry['state']='calling'
            with pytest.raises(writing.StopRun,match='uncertain_provider_result'):
                await writing.generate(ResearchSettings(),writing.Draft,writing.VOICE,{'sources':corpus},reserve)
            assert len(calls)==1
        finally:writing.CHECKPOINT_STORE.reset(token)
    database(operation)


@pytest.mark.parametrize('mode',['valid','incomplete','unknown','duplicate_key'])
def test_keyed_review_contract_and_final_binding(monkeypatch,mode):
    corpus=evidence.catalogue(EVIDENCE);draft=writing.resolve_grounded(grounded(corpus),corpus)
    def provider(config,payload):
        value=approved_payload(payload)
        checks={r.pop('target_id'):r for r in value.pop('checks')}
        value['checks']=checks
        if mode=='incomplete':checks.pop(next(iter(checks)))
        if mode=='unknown':next(iter(checks.values()))['fragment_ids']=['e_'+'0'*32]
        raw=json.dumps(value)
        if mode=='duplicate_key':raw=raw.replace('"approved": true','"approved": true, "approved": false')
        return raw,{'input_tokens':10,'output_tokens':100}
    monkeypatch.setattr(writing,'call',provider)
    async def reserve(cost):pass
    async def run():
        if mode=='duplicate_key':
            with pytest.raises(writing.StopRun,match='invalid_generation'):await writing.generate(ResearchSettings(),writing.Review,writing.REVIEW_INSTRUCTIONS,{'sources':corpus,'draft':draft.model_dump()},reserve)
            return
        review=await writing.generate(ResearchSettings(),writing.Review,writing.REVIEW_INSTRUCTIONS,{'sources':corpus,'draft':draft.model_dump()},reserve)
        assert review.approved==(mode=='valid')
        if review.approved:
            bound,metadata=writing.bind_reviewed_evidence(draft,review,corpus)
            assert len(writing.validate_draft(bound,corpus,[],metadata_refs=metadata).sources)==2
    asyncio.run(run())


@pytest.mark.parametrize('unfinished_summary',[False,True])
def test_manual_resume_uses_only_review_then_normal_publication(client,monkeypatch,unfinished_summary):
    corpus=evidence.catalogue(EVIDENCE);calls=[]
    def provider(config,payload):
        calls.append(payload['text']['format']['name'])
        return json.dumps(approved_payload(payload)),{'input_tokens':10,'output_tokens':100}
    monkeypatch.setattr(writing,'call',provider)
    async def operation(db):
        cfg=ResearchSettings();day=utcnow().astimezone(MADRID).date()
        db.add(ResearchControl(id=1,enabled=True))
        proposal=writing.resolve_grounded(grounded(corpus),corpus)
        if unfinished_summary:proposal.summary+=' Una frase que se queda sin terminar,'
        data=writing.validate_draft(proposal,corpus,[],provisional=True)
        article=Article(**data.model_dump(mode='json'),status='draft');db.add(article);await db.flush()
        report={'pending_review':True,'proposal':proposal.model_dump(mode='json'),'evidence':proposal.model_dump(mode='json'),'evidence_catalogue':corpus,'policy':{'kind':'news','min_organizations':2}}
        candidate=EditorialCandidate(fingerprint='manual-resume-test',engine='news',kind='news',topic=proposal.title,section='actualidad',intent='test',keyword='test',priority=80,state='deferred',details={'resume_report':report},article_id=article.id)
        db.add(candidate);await db.flush()
        job=EditorialExecution(mode='resume',request_key='manual-resume-request',candidate_id=candidate.id);db.add(job);await db.commit()
        await executions.prepare_job(db,job,cfg)
        assert job.state=='awaiting_approval' and not calls and job.max_reserved_microusd<150000
        job.state='queued';await db.commit()
        redis=Redis();redis.value=b'owner'
        async def verify(*a):return {'passed':True}
        # Public HTTP is covered separately; this asserts the durable pipeline boundary.
        async def finish(db,job,candidate,verifier=None):
            candidate.state='published';job.state='completed';await db.commit()
        monkeypatch.setattr(executions,'finish_verification',finish)
        await executions.execute_job(db,job,cfg,redis,b'owner')
        assert job.state=='completed' and article.status=='published'
        assert calls==['groundedreview']
        assert job.reserved_microusd<=job.max_reserved_microusd
        bucket=await db.get(ResearchRun,job.run_id)
        assert bucket.reserved_microusd==job.reserved_microusd and bucket.report['budget_bucket'] is True
    database(operation)


@pytest.mark.parametrize('cross_day',[False,True])
def test_verified_recovery_updates_original_day_without_resetting_budget_or_search(client,cross_day):
    from test_articles_api import article as article_payload
    from app.research.publication import article_snapshot
    async def operation(db):
        article=Article(**article_payload(),status='published',published_at=utcnow())
        db.add(article);await db.flush()
        candidate=EditorialCandidate(fingerprint='verified-day-recovery',engine='evergreen',kind='guide',
            topic=article.title,section=article.section,intent='test',keyword='test',state='needs_verification',
            article_id=article.id,details={'publication_snapshot':article_snapshot(article),'verification_attempts':0})
        db.add(candidate);await db.flush()
        web={'settled':True,'accounted_microusd':22558,'ledger_key':'saved-web-request'}
        bucket=ResearchRun(editorial_date=utcnow().astimezone(MADRID).date(),status='draft',reason='budget_exhausted',
            article_id=article.id,reserved_microusd=45613,report={'pending_review':True,'active_candidate_id':candidate.id,'web_research':web})
        db.add(bucket);await db.flush()
        funding=bucket
        if cross_day:
            from datetime import timedelta
            bucket.editorial_date-=timedelta(days=1)
            funding=ResearchRun(editorial_date=utcnow().astimezone(MADRID).date(),status='skipped',reserved_microusd=16000,report={'budget_bucket':True})
            db.add(funding);await db.flush()
        job=EditorialExecution(mode='resume',request_key='verified-day-recovery-job',run_id=funding.id,
            article_id=article.id,candidate_id=candidate.id,report={'review':{'approved':True}})
        db.add(job);await db.commit()
        async def verify(snapshot,page):return {'url':'https://example.test/articulos/'+snapshot['slug'],'html':True,'api':True,'seo':True,'sitemap':True,'image':True}
        for _ in range(2):await executions.finish_verification(db,job,candidate,verify)
        assert bucket.status=='published' and job.state=='completed'
        assert bucket.reserved_microusd==45613 and bucket.report['web_research']==web
        assert bucket.report['pending_review'] is False and bucket.report['recovered_by_execution']==job.id
        assert len(bucket.report['publications'])==1
        assert bucket.report['recovery_budget_run_id']==funding.id
        if cross_day:
            assert funding.reserved_microusd==16000 and funding.status=='published'
            assert funding.report['nightly_result_before_manual']['status']=='skipped'
            assert len(funding.report['manual_publications'])==1
    database(operation)


@pytest.mark.parametrize('bad_number',[False,True])
def test_approved_review_replays_after_final_validator_fix_without_new_provider_call(client,monkeypatch,bad_number):
    calls=[];corpus=evidence.catalogue(EVIDENCE)
    def provider(config,payload):
        calls.append('Review');return json.dumps(approved_payload(payload)),{'input_tokens':10,'output_tokens':100}
    monkeypatch.setattr(writing,'call',provider)
    async def operation(db):
        from app.research.checkpoints import store_for
        cfg=ResearchSettings();policy={'kind':'news','min_organizations':2}
        proposal=writing.resolve_grounded(grounded(corpus),corpus)
        if bad_number:proposal.paragraphs[0].text+=' El servicio procesa 999999 documentos.'
        data=writing.validate_draft(proposal,corpus,[],policy,provisional=True)
        article=Article(**data.model_dump(mode='json'),status='draft');db.add(article);await db.flush()
        run=ResearchRun(editorial_date=utcnow().astimezone(MADRID).date(),article_id=article.id,status='draft')
        db.add(run);await db.commit()
        async def reserve(cost):pass
        token=writing.CHECKPOINT_STORE.set(store_for(db,run))
        try:
            verdict=await writing.generate(cfg.model_copy(update={'max_output_tokens':writing.REVIEW_MAX_OUTPUT_TOKENS}),writing.Review,writing.REVIEW_INSTRUCTIONS,
                {'draft':proposal.model_dump(),'sources':corpus,'editorial_policy':policy},reserve)
        finally:writing.CHECKPOINT_STORE.reset(token)
        saved=dict(run.report,pending_review=False,corrections_used=1,proposal=proposal.model_dump(mode='json'),
            evidence=proposal.model_dump(mode='json'),evidence_catalogue=corpus,policy=policy,review=verdict.model_dump())
        candidate=EditorialCandidate(fingerprint='approved-review-replay',engine='news',kind='news',topic=proposal.title,
            section='actualidad',intent='test',keyword='test',state='deferred',article_id=article.id,details={'resume_report':saved})
        db.add(candidate);await db.flush()
        run.report=dict(saved,active_candidate_id=candidate.id)
        db.add(ResearchControl(id=1,enabled=True))
        job=EditorialExecution(mode='resume',request_key='approved-review-replay-job',candidate_id=candidate.id)
        db.add(job);await db.commit()
        await executions.prepare_job(db,job,cfg)
        if bad_number:
            assert job.state=='failed' and job.reason=='unsupported_number'
        else:
            assert job.state=='awaiting_approval' and job.max_reserved_microusd==0
            job.state='queued';await db.commit()
            redis=Redis();redis.value=b'owner'
            async def verify(snapshot,page):return {'url':'https://example.test/articulos/'+snapshot['slug'],'html':True,'api':True,'seo':True,'sitemap':True,'image':True}
            await executions.execute_job(db,job,cfg,redis,b'owner',verifier=verify)
            assert job.state=='completed' and article.status=='published' and run.status=='published'
            assert run.reserved_microusd==0 and job.reserved_microusd==0
        assert calls==['Review']
    database(operation)


@pytest.mark.parametrize('constraint',['job_cap','call_cap','daily','monthly','paused'])
def test_reservations_fail_before_provider(client,constraint):
    async def operation(db):
        day=utcnow().astimezone(MADRID).date()
        db.add(ResearchControl(id=1,enabled=constraint!='paused'))
        bucket=ResearchRun(editorial_date=day,reserved_microusd=149999 if constraint=='daily' else 0)
        job=EditorialExecution(request_key='reservation-budget-test',mode='auto',prepared={'max_calls':0 if constraint=='call_cap' else 1},max_reserved_microusd=1 if constraint=='job_cap' else 150000)
        db.add_all([bucket,job]);await db.commit()
        cfg=ResearchSettings()
        if constraint=='monthly':cfg=cfg.model_copy(update={'monthly_usd':0})
        with pytest.raises(writing.StopRun):await worker.reserve(db,executions.Context(job,bucket),cfg,1000)
        assert job.reserved_microusd==0
        assert bucket.reserved_microusd==(149999 if constraint=='daily' else 0)
    database(operation)


def test_approved_checkpoint_reuses_review_before_publication(client,monkeypatch):
    corpus=evidence.catalogue(EVIDENCE);calls=[]
    def provider(config,payload):
        calls.append(payload['text']['format']['name'])
        raw=grounded(corpus).model_dump_json() if calls[-1]=='groundeddraft' else json.dumps(approved_payload(payload))
        return raw,{'input_tokens':10,'output_tokens':100}
    monkeypatch.setattr(writing,'call',provider)
    async def operation(db):
        from app.research.quality import prepare
        row=ResearchRun(editorial_date=utcnow().date());db.add(row);await db.commit()
        async def reserve(cost):pass
        a,d=await prepare(db,row,ResearchSettings(),corpus,[],reserve,writing.generate)
        assert a.status=='draft' and calls==['groundeddraft','groundedreview']
        b,e=await prepare(db,row,ResearchSettings(),corpus,[],reserve,writing.generate,resume='review')
        assert a.id==b.id and d==e and len(calls)==2
        b.body+=' human change';await db.commit()
        with pytest.raises(writing.StopRun,match='article_changed'):await prepare(db,row,ResearchSettings(),corpus,[],reserve,writing.generate,resume='review')
        assert len(calls)==2
    database(operation)


def test_review_rebind_preserves_text_and_requires_two_body_organizations():
    corpus=evidence.catalogue(EVIDENCE)
    draft=writing.resolve_grounded(grounded(corpus),corpus)
    from app.research.evidence import targets
    checks=[writing.SupportCheck(target_id=t['target_id'],supported=True,fragment_ids=[corpus[0]['fragments'][0]['fragment_id']]) for t in targets(draft)]
    from test_research import review
    verdict=writing.GroundedReview(**review().model_dump(),checks=checks)
    # A second organization used only in metadata does not corroborate the body.
    verdict.checks[0].fragment_ids=[corpus[1]['fragments'][0]['fragment_id']]
    bound,metadata=writing.bind_reviewed_evidence(draft,verdict,corpus)
    with pytest.raises(writing.StopRun,match='insufficient_independent_sources'):writing.validate_draft(bound,corpus,[],metadata_refs=metadata)
    for check in verdict.checks:
        if check.target_id.startswith('p2.'):check.fragment_ids=[corpus[1]['fragments'][0]['fragment_id']]
    bound,metadata=writing.bind_reviewed_evidence(draft,verdict,corpus)
    assert len(writing.validate_draft(bound,corpus,[],metadata_refs=metadata).sources)==2
    assert [p.text for p in bound.paragraphs]==[p.text for p in draft.paragraphs]
    assert '[1, 1' not in writing.validate_draft(bound,corpus,[],metadata_refs=metadata).body


def test_incomplete_retry_is_bounded_and_never_applies_to_uncertain_results():
    from app.research.checkpoints import retryable_incomplete
    entry={'state':'failed','reason':'incomplete_generation','editorial_date':'2026-10-25','attempt_count':1}
    assert not retryable_incomplete(entry,'2026-10-25')
    assert retryable_incomplete(entry,'2026-10-26')
    assert not retryable_incomplete(dict(entry,attempt_count=2),'2026-10-27')
    assert not retryable_incomplete(dict(entry,state='uncertain'),'2026-10-26')
    assert not retryable_incomplete(dict(entry,reason='provider_unavailable'),'2026-10-26')


def test_request_hash_survives_jsonb_key_reordering():
    """PostgreSQL JSONB changes object key order, including nested policy/example."""
    corpus=evidence.catalogue(EVIDENCE)
    proposal=writing.resolve_grounded(grounded(corpus),corpus)
    policy={'kind':'news','min_organizations':2,'topic':'topic','internal_links':[['Guide','/tutoriales']]}
    original={'sources':corpus,'draft':proposal.model_dump(),'editorial_policy':policy}
    def reorder(v):
        if isinstance(v,dict):return {k:reorder(v[k]) for k in sorted(v,key=lambda k:(len(k),k))}
        if isinstance(v,list):return [reorder(i) for i in v]
        return v
    restored=reorder(original)
    assert restored==original
    first=writing.prepare_request(ResearchSettings(),writing.Review,writing.REVIEW_INSTRUCTIONS,original)
    second=writing.prepare_request(ResearchSettings(),writing.Review,writing.REVIEW_INSTRUCTIONS,restored)
    assert executions.digest(first[2])==executions.digest(second[2]) and first[-1]==second[-1]
