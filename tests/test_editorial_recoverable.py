"""Real saved failures, offline models, no paid or production mutation calls."""
import copy
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from html import escape

import pytest
from sqlalchemy import select,func

from test_research import client,database,Redis,EVIDENCE,draft
from test_editorial_engines import NOW,docs,no_news,receipt,verifier,provider_factory,tutorial_payload
from test_evidence_first import approved_payload
from app.models import Article,EditorialCandidate,ResearchRun,ResearchControl,EditorialLaneRun
from app.research import editorial,writing,lanes,queue,recovery,worker
from app.research.config import ResearchSettings
from app.research.publication import article_snapshot,verify_html,PublicationError
from app.research.seo import description

SAVED=json.loads((Path(__file__).parent/'fixtures/editorial_rejections_20261105.json').read_text(encoding='utf-8'))


def test_all_ten_real_rejections_retained_and_classified_without_fabricated_approvals():
    assert {c['id'] for c in SAVED['cases']}=={3,4,5,7,8,10,14,32,33,34}
    for case in SAVED['cases']:
        assert case['reason']
        if case['id'] in {7,14}:assert case['reason'] in recovery.FINAL
    sqlite=next(c for c in SAVED['cases'] if c['id']==3)
    assert sqlite['versions'][0]['review']['approved'] and not sqlite['versions'][0]['review']['original']
    from app.research.style import review_feedback,correction_plan
    feedback=review_feedback(sqlite['versions'][0]['review'])
    assert feedback['review_checks']['original'] is False and feedback['reasons']
    assert any('propio' in s for s in correction_plan(draft(),feedback)['required_actions'])


def test_real_public_descriptions_and_pydantic_long_lead_match_projection():
    failures=[r for r in SAVED['public_seo'] if not r['raw_equal']]
    assert len(failures)==6
    for r in SAVED['public_seo']:
        assert r['description']==description(r['summary'])
        assert r['canonical_ok'] and r['status']==200
    assert len(SAVED['pydantic_article']['summary'])==183


def getter_for(snapshot, *, noindex=False, bad_description=False):
    site='https://foroiaaldia.com';url=site+'/articulos/'+snapshot['slug']
    meta=description(snapshot['summary']) if not bad_description else 'Un texto ajeno'
    schema=[{'@type':['Article','BlogPosting'],'headline':snapshot['title'],'mainEntityOfPage':url,
        'datePublished':snapshot['published_at'],'dateModified':snapshot['updated_at'],
        'citation':[s['url'] for s in snapshot['sources']]},{'@type':'BreadcrumbList'}]
    body=snapshot['body']
    html=(f'<title>{escape(snapshot["title"])}</title><link rel="canonical" href="{url}">'
        f'<meta name="description" content="{escape(meta,quote=True)}">'
        f'<meta property="og:description" content="{escape(meta,quote=True)}">'
        f'<meta property="og:title" content="{escape(snapshot["title"],quote=True)}">'
        f'<meta property="og:image" content="{site}/image.png">'
        + ('<meta name="robots" content="noindex">' if noindex else '')
        +f'<script type="application/ld+json">{json.dumps(schema)}</script><h1>{escape(snapshot["title"])}</h1>'
        +escape(body.replace('`','').replace('*','')))
    responses={url:html,site+'/api/articles/'+snapshot['slug']:json.dumps(snapshot),site+'/image.png':b'image',
        site+'/sitemap.xml':f'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>{site}/sitemaps/articles/1</loc></sitemap></sitemapindex>',
        site+'/sitemaps/articles/1':f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{url}</loc></url></urlset>'}
    return lambda url:responses[url]


@pytest.mark.parametrize('mode',['valid','noindex','wrong_description'])
def test_public_verification_accepts_real_truncation_but_still_rejects_actual_seo_errors(mode):
    snapshot=copy.deepcopy(SAVED['pydantic_candidate']['details']['publication_snapshot'])
    get=getter_for(snapshot,noindex=mode=='noindex',bad_description=mode=='wrong_description')
    if mode=='valid':assert verify_html(snapshot,'https://foroiaaldia.com',1,get)['seo']
    else:
        with pytest.raises(PublicationError,match='publication_not_indexable'):verify_html(snapshot,'https://foroiaaldia.com',1,get)


@pytest.mark.parametrize('tamper',[False,True])
def test_real_pydantic_approval_recovers_same_article_without_model_calls(client,tmp_path,monkeypatch,tamper):
    from app.research import examples
    at=datetime(2026,11,5,16,tzinfo=UTC)
    path=receipt(tmp_path,at)
    data=json.loads(Path(path).read_text());data['runtime']={'python':'3.12.15','pydantic':'2.14.1'}
    Path(path).write_text(json.dumps(data))
    monkeypatch.setattr(writing,'call',lambda *a:pytest.fail('Recovery must not call a model'))
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True))
        a=copy.deepcopy(SAVED['pydantic_article'])
        for k,v in a.items():
            if k.endswith('_at') and v:a[k]=datetime.fromisoformat(v)
        article=Article(**a);db.add(article)
        c=copy.deepcopy(SAVED['pydantic_candidate'])
        for k,v in c.items():
            if k.endswith('_at') and v:c[k]=datetime.fromisoformat(v)
        candidate=EditorialCandidate(**c);db.add(candidate);await db.commit()
        candidate.state='publication_error'
        candidate.details=dict(candidate.details,withdrawal_snapshot=article_snapshot(article))
        if tamper:article.body+='\nCambio editorial posterior.'
        await db.commit()
        redis=Redis();redis.value=b'owner'
        if tamper:
            with pytest.raises(writing.StopRun,match='article_changed'):
                await recovery.recover_publication(db,candidate,ResearchSettings(),redis,b'owner',at,verifier,path)
            assert article.status=='archived'
        else:
            assert await recovery.recover_publication(db,candidate,ResearchSettings(),redis,b'owner',at,verifier,path)
            assert candidate.state=='published' and candidate.article_id==16
            assert article.status=='published' and article_snapshot(article)['published_at']==candidate.details['publication_snapshot']['published_at']
            assert await db.scalar(select(func.count(Article.id)))==1
            assert await recovery.recover_publication(db,candidate,ResearchSettings(),redis,b'owner',at,verifier,path)
    database(operation)


def test_rejected_review_resumes_only_directed_correction_next_day(client,tmp_path,monkeypatch):
    stamp=NOW
    monkeypatch.setattr(editorial,'utcnow',lambda:stamp);monkeypatch.setattr(worker,'utcnow',lambda:stamp)
    calls=[];base=provider_factory(calls);draft_calls=0
    def provider(config,payload):
        nonlocal draft_calls
        data=json.loads(payload['input']);kind=payload['text']['format']['name']
        raw,usage=base(config,payload);value=json.loads(raw)
        if kind=='evergreendraft':
            draft_calls+=1
            if data.get('errors'):
                assert 'original' in data['errors']['review_checks']
                assert data['errors']['editing_plan']['required_actions']
                value['paragraphs'][0]['text']+=' '+('La revisión se centra en los datos recibidos. ' * draft_calls)
        elif stamp==NOW:
            value.update(approved=True,original=False,reasons=[])
        return json.dumps(value),usage
    monkeypatch.setattr(writing,'call',provider)
    async def operation(db):
        nonlocal stamp
        db.add(ResearchControl(id=1,enabled=True));await queue.seed_evergreen(db)
        rows=(await db.scalars(select(EditorialCandidate).order_by(EditorialCandidate.id))).all()
        for c in rows[1:]:c.state='deferred';c.next_attempt_at=NOW+timedelta(days=10)
        first=ResearchRun(editorial_date=NOW.date(),report={});db.add(first);await db.commit()
        redis=Redis();redis.value=b'owner';config=ResearchSettings()
        options=dict(news_collector=no_news,doc_loader=docs,verifier=verifier,receipt_path=receipt(tmp_path))
        await editorial.execute(db,first,config,redis,b'owner',**options)
        c=rows[0];await db.refresh(c)
        assert c.state=='correction_pending' and c.details['resume_report']['corrections_used']==1
        aid=c.article_id;attempts=c.attempts
        stamp=NOW+timedelta(days=1)
        second=ResearchRun(editorial_date=stamp.date(),report={});db.add(second);await db.commit()
        await editorial.execute(db,second,config,redis,b'owner',**options)
        assert second.status=='published',second.report
        assert c.article_id==aid and c.attempts==attempts
        assert draft_calls==3  # Initial draft + one correction each day, never another initial draft.
        assert c.details['editorial_record']['corrections_used']==2
    database(operation)


def test_example_decoder_contract_and_test_only_support_are_safe(client,tmp_path):
    from app.research.evidence import catalogue
    from app.research.style import review_feedback
    async def operation(db):
        await queue.seed_evergreen(db);c=await db.scalar(select(EditorialCandidate))
        sources,policy=await queue.prepare_candidate(db,c,NOW,{'remaining':4},doc_loader=docs,receipt_path=receipt(tmp_path))
        sources=catalogue(sources)
        payload=writing.prepare_request(ResearchSettings(),writing.Draft,writing.VOICE,{'sources':sources,'editorial_policy':policy})[2]
        shape=payload['text']['format']['schema']['properties']['example_ids']
        assert shape['items']['enum']==[policy['example']['id']] and shape['minItems']==shape['maxItems']==1
        value=tutorial_payload(payload);resolved=writing.resolve_grounded(writing.EvergreenDraft.model_validate(value),sources)
        review_request=writing.prepare_request(ResearchSettings(),writing.Review,writing.REVIEW_INSTRUCTIONS,
            {'sources':sources,'draft':resolved.model_dump(),'editorial_policy':policy})[2]
        assert 'CUALQUIER fragmento' in review_request['instructions']
        verdict=writing.GroundedReview.model_validate(approved_payload(review_request))
        test_id='test_'+policy['example']['sha256']
        for check in verdict.checks:
            if check.target_id.startswith('p1.'):check.fragment_ids=[test_id]
        bound,_=writing.bind_reviewed_evidence(resolved,verdict,sources,policy)
        assert bound.paragraphs[0].evidence
        verdict.checks[2].fragment_ids=['test_'+'0'*64]
        with pytest.raises(writing.StopRun,match='invalid_review_coverage'):
            writing.bind_reviewed_evidence(resolved,verdict,sources,policy)
    database(operation)


def test_30_day_cost_simulation_with_real_usage_and_corrections_fits_proposal():
    import importlib.util
    spec=importlib.util.spec_from_file_location('capacity',Path(__file__).parents[1]/'scripts/simulate_editorial_capacity.py')
    capacity=importlib.util.module_from_spec(spec);spec.loader.exec_module(capacity)
    observed=json.loads((Path(__file__).parent/'fixtures/editorial_capacity_20261105.json').read_text())
    assert observed['sample_count']==68
    for days in (30,31):
        result=capacity.simulate(observed['samples'],observed['caps'],daily=500000,monthly=15000000,days=days,
            stressed=True,multiplier=2,practical_articles=2,corrections=2)
        assert result['hypothetical_articles']==3*days and result['accounted_microusd']<15000000
        assert all(r['peak_daily_reservation']<=500000 for r in result['records'])


@pytest.mark.parametrize('reason,expected',[('budget_exhausted','budget_pending'),('duplicate_topic','rejected'),
    ('insufficient_official_documentation','rejected'),('editorial_style_rejected','correction_pending'),
    ('uncertain_provider_result','technical_error')])
def test_recovery_states_are_distinct_and_never_invent_support(client,reason,expected):
    async def operation(db):
        await queue.seed_evergreen(db);c=await db.scalar(select(EditorialCandidate))
        c.details=dict(c.details,resume_report={'proposal':{'kept':True},'corrections_used':1})
        await queue.defer_or_reject(db,c,reason,NOW)
        assert c.state==expected and c.reason==reason
        assert c.details['resume_report']['proposal']=={'kept':True}
        assert recovery.disposition(c)['kind']!='pending'
    database(operation)


def test_budget_blocked_correction_keeps_attempt_for_next_execution(client,tmp_path,monkeypatch):
    from app.research import quality
    from app.research.evidence import catalogue
    calls=[]
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True));await queue.seed_evergreen(db)
        candidate=await db.scalar(select(EditorialCandidate))
        sources,policy=await queue.prepare_candidate(db,candidate,NOW,{'remaining':4},doc_loader=docs,receipt_path=receipt(tmp_path))
        sources=catalogue(sources)
        run=ResearchRun(editorial_date=NOW.date(),report={});db.add(run);await db.commit()
        async def budget(cost):raise writing.StopRun('budget_exhausted')
        async def model(config,schema,instructions,data,reserve):
            calls.append(schema.__name__)
            if schema is writing.Draft and data.get('errors'):
                await reserve(50000);pytest.fail('Unfunded correction cannot call provider')
            payload=writing.prepare_request(config,schema,instructions,data)[2]
            if schema is writing.Draft:return writing.resolve_grounded(writing.EvergreenDraft.model_validate(tutorial_payload(payload)),sources)
            verdict=writing.GroundedReview.model_validate(approved_payload(payload))
            verdict.approved=False;verdict.original=False;verdict.reasons=[]
            return verdict
        with pytest.raises(writing.StopRun,match='budget_exhausted'):
            await quality.prepare(db,run,ResearchSettings(),sources,[],budget,model,policy=policy)
        assert run.report['corrections_used']==0
        assert run.report['proposal'] and run.report['resume_correction']
        recovery.preserve(candidate,run.report,'budget_exhausted')
        await queue.defer_or_reject(db,candidate,'budget_exhausted',NOW)
        assert candidate.state=='budget_pending' and candidate.details['resume_report']['proposal']
    database(operation)


@pytest.mark.parametrize('failure',['none','news','first_practical'])
def test_three_slots_independent_budgeted_and_idempotent(client,tmp_path,monkeypatch,failure):
    monkeypatch.setattr(editorial,'utcnow',lambda:NOW);monkeypatch.setattr(lanes,'utcnow',lambda:NOW);monkeypatch.setattr(worker,'utcnow',lambda:NOW)
    news=[dict(s,published=NOW.isoformat()) for s in copy.deepcopy(EVIDENCE)]
    calls=[];base=provider_factory(calls,news=news)
    async def collector(now,urls):return ([] if failure=='news' else news),{'candidate_count':2}
    async def generator(config,schema,instructions,data,budget):
        if failure=='first_practical' and data.get('editorial_policy',{}).get('kind')!='news' and data.get('editorial_policy',{}).get('candidate_id')==1:
            raise writing.StopRun('provider_unavailable')
        return await writing.generate(config,schema,instructions,data,budget)
    def provider(config,payload):
        raw,usage=base(config,payload);value=json.loads(raw)
        if payload['text']['format']['name']=='evergreendraft':
            data=json.loads(payload['input']);cid=data['editorial_policy']['candidate_id']
            if cid!=1:
                value['title']='Guardar historiales de un asistente en SQLite sin repetir registros'
                value['slug']='guardar-historiales-asistente-sqlite'
                value['summary']='Un procedimiento para conservar registros identificados en una base de datos y actualizar sus campos de manera controlada.'
                for p in value['paragraphs']:p['text']=p['text'].replace('respuesta','registro').replace('documento','resumen').replace('validación','persistencia').replace('comprobación','preparación')
        return json.dumps(value),usage
    monkeypatch.setattr(writing,'call',provider)
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True));run=ResearchRun(editorial_date=NOW.date(),report={});db.add(run);await db.commit()
        redis=Redis();redis.value=b'owner'
        config=ResearchSettings(two_lanes=True,practical_publications=2,daily_usd='.50',monthly_usd='15')
        options=dict(news_collector=collector,doc_loader=docs,verifier=verifier,receipt_path=receipt(tmp_path),generator=generator)
        await lanes.execute(db,run,config,redis,b'owner',**options)
        rows=(await db.scalars(select(EditorialLaneRun).order_by(EditorialLaneRun.id))).all()
        assert [(r.engine,r.slot) for r in rows]==[('news',1),('evergreen',1),('evergreen',2)]
        assert run.report['planned_publications']==3
        assert 0<=run.reserved_microusd<=500000
        assert rows[2].status=='published',[(r.status,r.reason) for r in rows]
        if failure=='none':assert run.report['verified_publications']==3
        if failure=='news':assert run.report['verified_publications']==2
        if failure=='first_practical':assert rows[1].status!='published'
        before=len(calls);await lanes.execute(db,run,config,redis,b'owner',**options)
        assert len(calls)==before
    database(operation)
