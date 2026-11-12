"""Offline historical fixtures, simulated model/search; never production or paid calls."""
import asyncio
import copy
import inspect
import http.client
import json
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, func

from test_research import client, database, Redis
from test_rapid_news import documents, historical_draft
from test_evidence_first import approved_payload
from test_editorial_engines import docs, receipt, verifier
from app.models import Article, EditorialCandidate, ResearchControl, ResearchRun, GenerationUsage
from app.research import night_web, writing, editorial, sources, worker, queue, evidence
from app.research.config import ResearchSettings

NOW=datetime.fromisoformat(documents()[0]['published'])+timedelta(hours=1)


def nomination():
    return dict(title='OpenAI presents the GPT-4o multimodal model',
        event='The original GPT-4o announcement and documented integration conditions',
        date=NOW.date().isoformat(),organization='OpenAI',relevance='major_release',
        reason='A documented model announcement with practical implications for developers.',
        urls=[s['url'] for s in documents()])


def usage(**changes):
    return dict(input_tokens=8000,output_tokens=800,
        _web={'search_calls':1,'complete_output':True,'sources':nomination()['urls']},**changes)


async def seed(db):
    db.add(ResearchControl(id=1,enabled=True,rapid_enabled=False))
    run=ResearchRun(editorial_date=NOW.date(),report={},reserved_microusd=0)
    db.add(run);await db.commit();return run


def redis():
    result=Redis();result.value=b'owner';return result


def pages(url,limit):
    doc=next(s for s in documents() if s['url']==url)
    return url,('<meta property="article:published_time" content="'+doc['published']+'">'
        '<h1>'+doc['title']+'</h1><p>'+doc['text']+'</p>').encode()


def test_live_search_contract_and_worst_case_reservation():
    request=night_web.payload(ResearchSettings(),NOW,[])
    assert request['tools']==[{'type':'web_search','external_web_access':True,'search_context_size':'medium'}]
    assert request['max_tool_calls']==1 and request['tool_choice']=='required'
    assert request['parallel_tool_calls'] is False
    assert request['max_output_tokens']==5000
    assert night_web.maximum(ResearchSettings())==52768
    assert night_web.accounting(ResearchSettings(),usage())==(13600,1)
    assert all(name in request['instructions'] for name in ['Tesla','NVIDIA','xAI','DeepSeek','Anthropic'])


def test_real_numbered_paragraphs_are_not_quantities_and_actual_claims_still_need_support():
    fixture=json.loads((Path(__file__).parent/'fixtures/numbered_paragraphs_20261027.json').read_text(encoding='utf-8'))
    for p in fixture['paragraphs']:
        assert writing.factual_numbers(p['text'])==[]
        assert writing.factual_numbers(p['text']+' El servicio cuesta 999999 euros.')==['999999']
    assert writing.factual_numbers('Se publicaron 3 modelos y costaron 4 euros.')==['3','4']
    assert writing.factual_numbers('1) Primera tarea. 3) Otra tarea.')==['1','3']
    assert writing.factual_numbers('1) Primera tarea. 2) Cuesta 15 euros.')==['15']
    assert writing.factual_numbers('Python 3.12 procesa 100 registros.')==['3.12','100']


def test_unknown_model_pricing_and_daily_cap_fail_closed():
    with pytest.raises(writing.StopRun,match='web_model_tariff_unverified'):
        night_web.payload(ResearchSettings(model='gpt-5.4-mini',input_per_million=Decimal('.75'),output_per_million=Decimal('4.5')),NOW,[])
    with pytest.raises(ValueError):ResearchSettings(daily_usd=Decimal('.500001'))


def test_discovery_schema_allows_single_original_and_requires_diagnostics():
    item=nomination();item['urls']=item['urls'][:1]
    assert night_web.NewsOpportunity.model_validate(item).urls==item['urls']
    request=night_web.payload(ResearchSettings(),NOW,[])
    shape=request['text']['format']['schema']
    assert set(shape['required'])=={'candidates','search_summary','empty_reason','discarded'}
    assert shape['properties']['candidates']['maxItems']==10
    assert night_web.maximum(ResearchSettings(),request)<79242


def test_one_invalid_candidate_does_not_discard_valid_candidates(client):
    invalid=dict(nomination(),urls=[])
    def provider(*a):return json.dumps({'candidates':[invalid,nomination()],'search_summary':'Two isolated fixture proposals.'}),usage()
    async def operation(db):
        run=await seed(db)
        found,report=await night_web.research(db,run,ResearchSettings(),redis(),b'owner',NOW,provider)
        assert len(found)==1 and report['research_status']=='candidates_found'
        assert report['returned_candidates']==2 and report['invalid_candidates'][0]['index']==0
        assert run.report['web_research']['invalid_candidates']==report['invalid_candidates']
    database(operation)


def test_old_real_empty_reply_is_diagnosed_not_declared_success(client):
    async def operation(db):
        run=await seed(db)
        found,report=await night_web.research(db,run,ResearchSettings(),redis(),b'owner',NOW,
            lambda *a:('{"candidates":[]}',usage()))
        assert not found and report['research_status']=='empty'
        assert report['reason']=='no_candidates_reported'
        assert report['empty_reason']=='provider_did_not_explain_empty_result'
    database(operation)


def test_failed_search_tool_is_not_a_successful_empty_research(client):
    data=usage();data['_web']['tool_calls']=[{'action':'search','status':'failed'}]
    async def operation(db):
        run=await seed(db)
        found,report=await night_web.research(db,run,ResearchSettings(),redis(),b'owner',NOW,
            lambda *a:('{"candidates":[],"empty_reason":"Search unavailable"}',data))
        assert not found and report['research_status']=='invalid' and report['reason']=='web_search_tool_failed'
    database(operation)


def test_first_rejected_proposal_does_not_block_next_verified_proposal(client):
    first=dict(nomination(),title='Unverified synthetic event candidate',event='An unrelated synthetic hardware event',urls=['https://127.0.0.1/private'])
    async def operation(db):
        run=await seed(db)
        report=await night_web.discover(db,run,ResearchSettings(),redis(),b'owner',NOW,
            lambda *a:(json.dumps({'candidates':[first,nomination()]}),usage()),pages,recovery_feeds=())
        assert report['opportunities'][0]['reason_for_decision']=='domain_not_allowed'
        assert report['opportunities'][1]['reason_for_decision']=='verified_queued'
        assert report['web']['verified_candidates']==1
    database(operation)


def test_single_original_avoids_unnecessary_corroboration_search(client):
    from email.utils import format_datetime
    item=nomination();item['urls']=item['urls'][:1]
    second=documents()[1]
    feed=sources.Feed('https://www.microsoft.com/isolated-fixture-feed','www.microsoft.com','microsoft')
    calls=[]
    def provider(*a):calls.append(1);return json.dumps({'candidates':[item]}),usage()
    def fetch(url,limit):
        if url==feed.url:
            return url,('<rss><channel><item><title>'+second['title']+'</title><link>'+second['url']+'</link><pubDate>'+format_datetime(datetime.fromisoformat(second['published']))+'</pubDate></item></channel></rss>').encode()
        return pages(url,limit)
    async def operation(db):
        run=await seed(db)
        report=await night_web.discover(db,run,ResearchSettings(),redis(),b'owner',NOW,provider,fetch,recovery_feeds=[feed])
        assert report['web']['verified_candidates']==1 and report['statistics']['documents']==1
        assert not report['related_recovery']
        assert report['opportunities'][0]['verification']['verification_mode']=='official_announcement'
    database(operation)
    assert calls==[1]


def test_unexplained_empty_search_does_not_trigger_evergreen(client,tmp_path,monkeypatch):
    calls=[]
    def provider(config,payload):calls.append(payload['text']['format']['name']);return '{"candidates":[]}',usage()
    monkeypatch.setattr(writing,'call',provider);monkeypatch.setattr(editorial,'utcnow',lambda:NOW)
    async def operation(db):
        run=await seed(db)
        await editorial.execute(db,run,ResearchSettings(),redis(),b'owner',doc_loader=docs,verifier=verifier,receipt_path=receipt(tmp_path,NOW))
        assert run.status=='skipped' and run.reason=='research_failed_no_evergreen_substitution'
        assert await db.scalar(select(func.count(Article.id)))==0
    database(operation)
    assert calls==['newsresearch']


def test_repeated_technical_evergreen_is_deferred_before_fetch_or_generation(client):
    from test_articles_api import article as article_payload
    async def operation(db):
        await queue.seed_evergreen(db)
        rows=(await db.scalars(select(EditorialCandidate))).all()
        for row in rows[:2]:
            article=Article(**{**article_payload(),'slug':'fixture-existing-'+str(row.id)},status='published',published_at=NOW-timedelta(days=1))
            db.add(article);await db.flush();row.article_id=article.id;row.state='published';row.published_at=NOW-timedelta(days=1)
        target=next(r for r in rows if r.details['blueprint']=='save-summaries')
        await db.commit()
        async def forbidden(*a):pytest.fail('Cooldown must run before downloading documents')
        with pytest.raises(writing.StopRun,match='evergreen_topic_cooldown'):
            await queue.prepare_candidate(db,target,NOW,{'remaining':4},doc_loader=forbidden)
        await queue.defer_or_reject(db,target,'evergreen_topic_cooldown',NOW)
        assert target.state=='deferred' and target.attempts==0
    database(operation)


@pytest.mark.parametrize('funded',[True,False])
@pytest.mark.parametrize('bucket_kind',['web','manual_bucket'])
def test_authorized_news_retry_keeps_day_history_budget_and_schedule(client,monkeypatch,funded,bucket_kind):
    from contextlib import asynccontextmanager
    from test_articles_api import article as article_payload
    monkeypatch.setattr(worker,'utcnow',lambda:NOW)
    monkeypatch.setattr(worker,'settings',lambda:ResearchSettings(api_key='offline-not-a-key'))
    r=Redis();monkeypatch.setattr(worker,'get_redis',lambda:r)
    calls=[]
    async def operation(db):
        article=Article(**article_payload(),status='published',published_at=NOW);db.add(article);await db.flush()
        db.add(ResearchControl(id=1,enabled=True))
        original={'web_research':{'state':'response','settled':True},'previous_publication':'preserved'} if bucket_kind=='web' else {'budget_bucket':True}
        run=ResearchRun(editorial_date=NOW.date(),status='published',reason='quality_checks_passed',article_id=article.id,
            reserved_microusd=70758 if funded else 149000,report=copy.deepcopy(original),finished_at=NOW)
        db.add(run);await db.flush()
        if bucket_kind=='manual_bucket':
            from app.models import EditorialExecution
            db.add(EditorialExecution(mode='resume',request_key='fixture-completed-manual',run_id=run.id,article_id=article.id,state='completed'))
        await db.commit()
        @asynccontextmanager
        async def session():yield db
        monkeypatch.setattr(worker,'get_sessionmaker',lambda:session)
        async def execute(db,row,config,redis,token,**kwargs):
            calls.append(kwargs);assert row.id==run.id and row.reserved_microusd==70758
            assert row.report['prior_attempts'][0]['report']==original
            row.status='skipped';row.reason='no_verified_news';row.finished_at=NOW;await db.commit()
        monkeypatch.setattr(editorial,'execute',execute)
        if funded:
            await worker.retry_news(run.id)
            assert calls==[{'max_publications':1,'allow_evergreen':False}]
            assert run.status=='published' and run.article_id==article.id and run.reserved_microusd==70758
            assert run.report['manual_news_retry']['result']['new_article_id'] is None
            with pytest.raises(writing.StopRun,match='news_retry_not_eligible'):await worker.retry_news(run.id)
            saved=dict(run.report,web_research={'state':'response','settled':True,'raw':'{"candidates":[]}'})
            run.report=saved;await db.commit()
            await worker.retry_news(run.id,resume=True)
            assert run.report['research_attempt_key']==saved['research_attempt_key']
            assert run.report['web_research']==saved['web_research']
            assert len(run.report['news_continuations'])==1
            assert run.reserved_microusd==70758 and run.article_id==article.id
        else:
            with pytest.raises(writing.StopRun,match='budget_exhausted'):await worker.retry_news(run.id)
            assert not calls and run.report==original and run.reserved_microusd==149000
        assert worker.settings().at.isoformat()=='22:30:00'
    database(operation)


@pytest.mark.parametrize('change',[{'input_tokens':400001},{'output_tokens':5001},{'input_tokens':True},
    {'_web':{'search_calls':2,'complete_output':True}}, {'_web':{'search_calls':1,'complete_output':False}}])
def test_invalid_accounting_never_releases_a_reservation(change):
    data=usage();data.update(change)
    with pytest.raises((ValueError,KeyError)):night_web.accounting(ResearchSettings(),data)


def test_research_settles_only_confirmed_usage_and_replays_without_second_call(client):
    calls=[]
    def provider(config,payload):
        calls.append(payload)
        return json.dumps({'candidates':[nomination()]}),usage()
    async def operation(db):
        run=await seed(db)
        first,report=await night_web.research(db,run,ResearchSettings(),redis(),b'owner',NOW,provider)
        assert len(first)==1 and report['accounted_microusd']==13600
        assert run.reserved_microusd==13600
        second,_=await night_web.research(db,run,ResearchSettings(),redis(),b'owner',NOW,provider)
        assert first==second and len(calls)==1
        assert await db.scalar(select(func.count(GenerationUsage.id)))==1
        assert (await db.scalar(select(GenerationUsage))).candidate_id is None
    database(operation)


@pytest.mark.parametrize('state',['calling','failed'])
def test_crash_or_uncertain_result_keeps_money_and_never_retries(client,state):
    async def operation(db):
        run=await seed(db);run.reserved_microusd=116000
        run.report={'web_research':{'state':state,'ledger_key':'a'*64,'reserved_microusd':116000}}
        await db.commit()
        found,report=await night_web.research(db,run,ResearchSettings(),redis(),b'owner',NOW,
            lambda *a:pytest.fail('Uncertain requests cannot be repeated'))
        assert found==[] and run.reserved_microusd==116000
    database(operation)


def test_real_saved_tool_usage_can_settle_within_original_reservation_without_new_search(client):
    fixture=json.loads((Path(__file__).parent/'fixtures/web_research_usage_20261027.json').read_text())
    cost,calls=night_web.accounting(ResearchSettings(),fixture['usage'],fixture['input_bound'],fixture['reserved_microusd'])
    assert cost==22558 and calls==2
    with pytest.raises(ValueError):night_web.accounting(ResearchSettings(),fixture['usage'],fixture['input_bound'],21000)
    async def operation(db):
        run=await seed(db);run.reserved_microusd=fixture['reserved_microusd']+23055
        run.report={'web_research':{'state':'response','raw':fixture['raw'],'usage':fixture['usage'],
            'ledger_key':'d'*64,'reserved_microusd':fixture['reserved_microusd'],'input_bound':fixture['input_bound']}}
        await db.commit()
        def forbidden(*a):pytest.fail('Settling a known response must never call the provider')
        for _ in range(2):
            found,report=await night_web.research(db,run,ResearchSettings(),redis(),b'owner',NOW,forbidden)
            assert not found and report['observed_tool_limit_exceeded']
            assert run.reserved_microusd==45613  # draft reservation remains untouched
        assert await db.scalar(select(func.count(GenerationUsage.id)))==1
    database(operation)


@pytest.mark.parametrize('limit',['daily','monthly'])
def test_no_budget_makes_no_search_call(client,limit):
    async def operation(db):
        run=await seed(db)
        if limit=='daily':run.reserved_microusd=100000
        else:db.add(ResearchRun(editorial_date=NOW.date()-timedelta(days=1),reserved_microusd=4980000))
        await db.commit()
        found,report=await night_web.research(db,run,ResearchSettings(),redis(),b'owner',NOW,
            lambda *a:pytest.fail('No budget means no paid call'))
        assert not found and report['state']=='unfunded'
    database(operation)


@pytest.mark.parametrize('mode',['valid','same_publisher','old','blocked','truncated','unsafe','duplicate','no_search','unrelated'])
def test_search_candidates_must_pass_real_source_gate(client,mode):
    item=nomination();payload={'candidates':[item]};data=usage();fetches=[]
    if mode!='valid':item['event']+=' Objective comparison requiring corroboration.'
    if mode=='same_publisher':item['urls'][1]='https://openai.com/index/same-publisher-fixture'
    if mode=='unsafe':item['urls']=['https://127.0.0.1/private','https://evil.test/internal']
    if mode=='no_search':data['_web']['search_calls']=0
    def fetch(url,limit):
        fetches.append(url)
        if mode=='blocked':raise sources.SourceError('Denied','http_status',403)
        if mode=='truncated':raise http.client.IncompleteRead(b'broken')
        if mode=='same_publisher' and 'same-publisher' in url:
            _,body=pages(nomination()['urls'][1],limit);return url,body
        final,body=pages(url,limit)
        if mode=='old':body=body.replace(documents()[0]['published'].encode(),b'2020-01-01T12:00:00+00:00')
        if mode=='unrelated' and url==nomination()['urls'][1]:
            body=body.replace(documents()[0]['title'].encode(),b'NVIDIA introduces Blackwell')
        return final,body
    async def operation(db):
        run=await seed(db)
        if mode=='duplicate':
            from test_articles_api import article
            db.add(Article(**{**article(),'sources':[{'url':item['urls'][0],'title':'Existing','language':'en'}]},status='published'))
            await db.commit()
        report=await night_web.discover(db,run,ResearchSettings(),redis(),b'owner',NOW,
            lambda *a:(json.dumps(payload),data),fetch,recovery_feeds=())
        candidates=(await db.scalars(select(EditorialCandidate).where(EditorialCandidate.engine=='news'))).all()
        if mode=='valid':
            assert len(candidates)==1 and candidates[0].state=='ready'
            assert len(candidates[0].details['sources'])==2
            assert report['opportunities'][0]['reason_for_decision']=='verified_queued'
            # Re-running discovery uses the stored search and event identity.
            await night_web.discover(db,run,ResearchSettings(),redis(),b'owner',NOW,
                lambda *a:pytest.fail('Stored research reused'),fetch,recovery_feeds=())
            assert await db.scalar(select(func.count(EditorialCandidate.id)))==1
        else:
            assert not candidates,report
            if mode=='blocked':assert all(e['http_status']==403 for e in report['statistics']['fetch_errors'])
            if mode in {'unsafe','no_search'}:assert not fetches
    database(operation)


def test_nightly_full_flow_uses_search_then_existing_generation_review_and_publication(client,tmp_path,monkeypatch):
    calls=[]
    monkeypatch.setattr(editorial,'utcnow',lambda:NOW)
    monkeypatch.setattr(sources,'fetch',pages)
    def provider(config,payload):
        kind=payload['text']['format']['name'];calls.append(kind)
        if kind=='newsresearch':return json.dumps({'candidates':[nomination()]}),usage()
        value=historical_draft(json.loads(payload['input'])['sources']) if kind=='groundeddraft' else approved_payload(payload)
        return json.dumps(value),{'input_tokens':1000,'output_tokens':800}
    monkeypatch.setattr(writing,'call',provider)
    async def operation(db):
        run=await seed(db)
        await editorial.execute(db,run,ResearchSettings(),redis(),b'owner',verifier=verifier,
            doc_loader=docs,receipt_path=receipt(tmp_path,NOW))
        assert run.status=='published',run.report
        assert len(run.report['publications'])==1
        assert (await db.scalar(select(Article).where(Article.status=='published'))).slug=='fixture-gpt4o-historical-isolated'
        assert len((await db.scalars(select(GenerationUsage))).all())==3
        assert run.reserved_microusd<=150000 and run.report['web_research']['settled']
    database(operation)
    assert calls==['newsresearch','groundeddraft','groundedreview']


def test_empty_web_news_falls_back_to_evergreen(client,tmp_path,monkeypatch):
    from test_editorial_engines import provider_factory
    calls=[];normal=provider_factory(calls)
    def provider(config,payload):
        if payload['text']['format']['name']=='newsresearch':return json.dumps({'candidates':[],'empty_reason':'No fixture announcements in this isolated test.'}),usage()
        return normal(config,payload)
    monkeypatch.setattr(writing,'call',provider);monkeypatch.setattr(editorial,'utcnow',lambda:NOW)
    async def operation(db):
        run=await seed(db)
        await editorial.execute(db,run,ResearchSettings(),redis(),b'owner',verifier=verifier,
            doc_loader=docs,receipt_path=receipt(tmp_path,NOW))
        assert run.status=='published' and run.report['engine']=='evergreen',run.report
        assert run.reserved_microusd<=150000
    database(operation)


def test_periodic_news_and_daytime_dispatch_are_not_started():
    source=inspect.getsource(worker.main)
    assert 'rapid.loop' not in source and 'rapid.dispatch' not in source
    assert 'await tick()' in source


@pytest.mark.parametrize('maximum',[None,1])
def test_two_distinct_verified_news_can_publish_in_one_run(client,tmp_path,monkeypatch,maximum):
    """Two simulated articles, real validation/review adapter/publication, isolated DB."""
    first=documents();second=copy.deepcopy(first)
    for i,s in enumerate(second):
        s.update(id=i+30,title='NVIDIA announces Blackwell computing architecture',
            url='https://blogs.nvidia.com/blog/fixture-blackwell' if i==0 else 'https://www.microsoft.com/en-us/research/fixture-blackwell',
            organization='nvidia' if i==0 else 'microsoft',
            text=('NVIDIA introduced the Blackwell architecture for accelerated computing. '
                  'The announcement describes computing hardware and integration conditions. ' if i==0 else
                  'This independent synthetic document discusses the Blackwell hardware announcement. '
                  'Deployment and evaluation require reviewing the available system documentation. ')*12)
    calls=[]
    def provider(config,payload):
        kind=payload['text']['format']['name'];calls.append(kind)
        data=json.loads(payload['input'])
        if kind=='groundedreview':value=approved_payload(payload)
        elif data['sources'][0]['organization']=='openai':value=historical_draft(data['sources'])
        else:
            refs=[{'fragment_id':data['sources'][0]['fragments'][0]['fragment_id']}]
            value={'title':'Blackwell: arquitectura de computación y límites de su anuncio',
                'slug':'fixture-blackwell-isolated','summary':'Una lectura de las fuentes sobre una arquitectura de computación, sus condiciones de integración y los aspectos que requieren evaluación.',
                'section':'actualidad','title_evidence':refs,'summary_evidence':refs,
                'paragraphs':[{'heading':h,'text':text,'evidence':[{'fragment_id':data['sources'][i%2]['fragments'][0]['fragment_id']}]} for i,(h,text) in enumerate([
                    ('Una propuesta de infraestructura','La arquitectura presentada se sitúa en el ámbito de la computación acelerada. El anuncio aporta una referencia para conocer el enfoque del fabricante y no debe confundirse con una prueba independiente. Para entender su alcance conviene distinguir los componentes descritos de los resultados que cada aplicación pueda obtener al utilizarlos.'),
                    ('Condiciones para integrar hardware','Integrar hardware en una infraestructura requiere revisar su documentación y las condiciones del sistema. La fuente complementaria permite contextualizar esa tarea sin afirmar que se haya instalado ningún equipo. Una decisión técnica necesita atender al entorno de uso, a sus restricciones y a las responsabilidades de quienes lo mantienen.'),
                    ('Cómo leer las fuentes disponibles','Las publicaciones consultadas se refieren al mismo anuncio y ofrecen un punto de partida documental. Las afirmaciones del fabricante conservan ese alcance y no se presentan como mediciones hechas por esta redacción. La perspectiva complementaria ayuda a formular las preguntas que habría que resolver antes de escoger una infraestructura.'),
                    ('Lo que requiere evaluación propia','El lector puede utilizar las referencias para preparar su análisis técnico y contrastar las condiciones de despliegue. Este texto no ofrece cifras de rendimiento ni atribuye resultados a pruebas inexistentes. Una evaluación posterior debería documentar su entorno y sus criterios para que las conclusiones puedan entenderse dentro de su contexto.')])]}
        return json.dumps(value),{'input_tokens':1000,'output_tokens':800}
    async def collected(now,urls):return first+second,{'candidate_count':2}
    monkeypatch.setattr(writing,'call',provider);monkeypatch.setattr(editorial,'utcnow',lambda:NOW)
    async def operation(db):
        run=await seed(db)
        await editorial.execute(db,run,ResearchSettings(),redis(),b'owner',news_collector=collected,
            verifier=verifier,receipt_path=receipt(tmp_path,NOW),max_publications=maximum)
        expected=1 if maximum==1 else 2
        assert len(run.report['publications'])==expected,run.report
        assert await db.scalar(select(func.count(Article.id)).where(Article.status=='published'))==expected
        assert run.reserved_microusd<=150000
    database(operation)
    assert calls==['groundeddraft','groundedreview']*(1 if maximum==1 else 2)


def test_saved_markdown_urls_are_unwrapped_without_weakening_fetch_policy():
    value=nomination()
    value['urls']=['([openai.com](https://openai.com/index/fixture-news?utm_source=openai))']
    item=night_web.NewsOpportunity.model_validate(value)
    assert item.urls==['https://openai.com/index/fixture-news?utm_source=openai']
    with pytest.raises(sources.SourceError):
        sources.canonical('https://127.0.0.1/news/unsafe')


def test_publication_stamp_uses_explicit_date_and_ignores_modification_and_sidebar():
    from datetime import UTC,datetime
    stamp,precision=sources.publication_stamp(b'<div class="article-date">October 26, 2026</div><aside>October 27, 2026</aside>')
    assert stamp==datetime(2026,10,26,tzinfo=UTC) and precision=='calendar_day'
    assert sources.publication_stamp(b'{"dateModified":"2026-10-27T10:00:00Z"}<aside>October 27, 2026</aside>')[0] is None


def test_publisher_index_links_are_bounded_and_never_evidence_themselves():
    html=b'<nav><a href="/news/navigation">Navigation ignored</a></nav><a href="/news/">News overview</a><a href="/news/verified-event">October 26, 2026 A specific announcement</a><a href="http://127.0.0.1/">Unsafe destination</a>'
    links=sources.news_links(html,'https://nvidianews.nvidia.com/news/',True)
    assert len(links)==1
    assert links[0]['url']=='https://nvidianews.nvidia.com/news/verified-event'
    assert links[0]['published'].startswith('2026-10-26')


def test_sidebar_links_are_not_independent_corroboration():
    raw=b'<article><h1>Original event</h1><p>Actual article text.</p></article><aside><a href="https://www.microsoft.com/en-us/research/other">Unrelated editorial recommendation</a></aside>'
    assert sources.news_links(raw,'https://openai.com/index/original')==[]
    assert 'recommendation' not in sources.plain(raw)


def test_public_offering_cross_language_relation_requires_same_subject():
    from app.research.selection import relationship
    a={'title':'Anthropic presenta documentos para su salida a bolsa','text':''}
    b={'title':'Anthropic files S-1 for proposed initial public offering','text':''}
    assert 'initial_public_offering' in relationship(a,b)['concepts']


def test_blocked_nomination_recovers_original_from_curated_html_and_existing_search_urls(client):
    docs=copy.deepcopy(documents())
    docs[1]['url']='https://www.microsoft.com/news/research-fixture'
    feed=sources.Feed('https://openai.com/news','openai.com','openai',kind='html')
    second=sources.Feed('https://www.microsoft.com/news','www.microsoft.com','microsoft',kind='html')
    proposed=nomination();proposed['urls']=['https://openai.com/index/blocked-fixture']
    def fetch(url,limit):
        if url==proposed['urls'][0]:raise sources.SourceError('Blocked','http_status',403)
        if url==feed.url:
            return url,('<a href="'+docs[0]['url']+'">'+docs[0]['title']+'</a>').encode()
        if url==second.url:return url,('<a href="'+docs[1]['url']+'">'+docs[1]['title']+'</a>').encode()
        d=next(d for d in docs if d['url']==url)
        return url,('<meta property="article:published_time" content="'+d['published']+'"><h1>'+d['title']+'</h1><p>'+d['text']+'</p>').encode()
    async def operation(db):
        run=await seed(db)
        result=await night_web.discover(db,run,ResearchSettings(),redis(),b'owner',NOW,
            lambda *a:(json.dumps({'candidates':[proposed]}),usage()),fetch,recovery_feeds=(feed,second))
        assert result['web']['verified_candidates']==1,result
        assert result['opportunities'][0]['reason_for_decision']=='verified_queued'
        assert result['statistics']['documents']==1
    database(operation)


@pytest.mark.parametrize('mode',['valid','uncertain','missing_usage','wrong_run','over_bound'])
def test_settlement_releases_only_proven_reserves_and_survives_old_report_replay(client,mode):
    from app.research.checkpoints import settle_completed
    async def operation(db):
        run=await seed(db)
        entry={'state':'response','editorial_date':str(run.editorial_date),'ledger_key':'fixture-settle',
            'stage':'Draft','maximum_microusd':16000,'usage':{'input_tokens':1000,'output_tokens':1000}}
        if mode=='uncertain':entry['state']='uncertain'
        if mode=='missing_usage':entry['usage']={}
        ledger_run=run.id
        if mode=='wrong_run':
            other=ResearchRun(editorial_date=run.editorial_date-timedelta(days=1));db.add(other);await db.flush();ledger_run=other.id
        amount=20000 if mode=='over_bound' else 2250
        db.add(GenerationUsage(run_id=ledger_run,model='gpt-5-mini',stage='Draft',request_key='fixture-settle',
            input_tokens=1000,output_tokens=1000,cached_tokens=0,estimated_microusd=amount))
        run.report={'stage_checkpoints':{'key':entry}};run.reserved_microusd=30000
        await db.commit();old=copy.deepcopy(run.report)
        await settle_completed(db,run,ResearchSettings())
        expected=16250 if mode=='valid' else 30000
        assert run.reserved_microusd==expected
        run.report=old;await db.commit()
        await settle_completed(db,run,ResearchSettings())
        assert run.reserved_microusd==expected
    database(operation)
