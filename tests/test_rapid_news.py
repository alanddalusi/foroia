"""Offline RSS/network/model fixtures; no paid calls or production writes."""
import asyncio,copy,json
from contextlib import asynccontextmanager
from datetime import UTC,datetime,timedelta
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urlsplit
import pytest
from sqlalchemy import select,func
from test_research import client,database,Redis,EVIDENCE
from test_accounts_api import app_override
from test_articles_api import AUTH
from test_evidence_first import approved_payload
from app.models import ResearchControl,ResearchRun,EditorialCandidate,EditorialExecution,NewsScan,NewsObservation,Article
from app.research import rapid,events,queue,sources,worker,executions,writing,evidence
from app.research.config import ResearchSettings,MADRID,due

FIXTURES=json.loads((Path(__file__).parent/'fixtures/historical_ai_events.json').read_text())['events']

def feed_for(event):return sources.Feed('https://'+urlsplit(event['url']).hostname+'/test-fixture-feed.xml',urlsplit(event['url']).hostname,event['entity'])
def rss(event,stamp=None):
    stamp=stamp or datetime.fromisoformat(event['published'])
    return ('<rss><channel><item><title>'+event['title']+'</title><link>'+event['url']+'</link><pubDate>'+format_datetime(stamp)+'</pubDate></item></channel></rss>').encode()
def html(event):
    return ('<html><head><meta property="article:published_time" content="'+event['published']+'"></head><body><h1>'+event['title']+'</h1><p>'+event['fact']+' Additional fixture context about documentation and checking announcement scope.'*16+'</p></body></html>').encode()

@pytest.mark.parametrize('event',FIXTURES,ids=lambda e:e['entity'])
def test_verified_historical_facts_detected_without_generation(client,event,monkeypatch):
    now=datetime.fromisoformat(event['published'])+timedelta(hours=1);feed=feed_for(event);calls=[]
    monkeypatch.setattr(writing,'call',lambda *a:pytest.fail('Detection must never call OpenAI'))
    def fetch(url,limit):calls.append(url);return url,rss(event) if url==feed.url else html(event)
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True,rapid_enabled=True));scan=NewsScan(window=rapid.window(now));db.add(scan);await db.commit()
        report=await rapid.observe(db,scan,now,fetch,[feed]);assert report['model_calls']==0 and report['documents']==1
        c=await db.scalar(select(EditorialCandidate));assert c.details['event']['entity']==event['entity'] and c.details['event']['product']==event['product']
        assert c.details['event']['category']==event['category'] and c.state=='queued'
        # Editing RSS title/date or restarting cannot create a second event for this URL.
        second=NewsScan(window=rapid.window(now+timedelta(minutes=30)));db.add(second);await db.commit()
        report=await rapid.observe(db,second,now+timedelta(minutes=30),lambda u,n:(u,rss(dict(event,title='Updated '+event['title']),now+timedelta(minutes=20))),[feed])
        assert report['already_seen']==1 and report['article_fetches']==0
        assert await db.scalar(select(func.count()).select_from(EditorialCandidate))==1
    database(operation)

@pytest.mark.parametrize('event',FIXTURES,ids=lambda e:e['entity'])
def test_historical_events_never_become_current_news(client,event):
    now=datetime(2026,10,26,12,tzinfo=UTC);feed=feed_for(event)
    async def operation(db):
        scan=NewsScan(window=now);db.add(scan);await db.commit()
        report=await rapid.observe(db,scan,now,lambda u,n:(u,rss(event)),[feed])
        assert report['documents']==report['article_fetches']==0
        assert report['rejected'][0]['reason']=='stale_announcement'
        assert not await db.scalar(select(EditorialCandidate.id))
    database(operation)

def test_changed_rss_date_cannot_hide_old_page_publication(client):
    event=FIXTURES[2];now=datetime(2026,10,26,12,tzinfo=UTC);feed=feed_for(event)
    def fetch(url,limit):return url,rss(event,now) if url==feed.url else html(event)
    async def operation(db):
        scan=NewsScan(window=now);db.add(scan);await db.commit();report=await rapid.observe(db,scan,now,fetch,[feed])
        assert report['rejected'][0]['reason']=='old_article_updated' and not report['accepted']
    database(operation)


def test_blocked_announcements_enter_existing_queue_without_becoming_verified_evidence(client,monkeypatch):
    event=FIXTURES[2];now=datetime.fromisoformat(event['published']);feed=feed_for(event)
    monkeypatch.setattr(writing,'call',lambda *a:pytest.fail('RSS metadata cannot authorize generation'))
    def fetch(url,limit):
        if url==feed.url:return url,rss(event)
        raise sources.SourceError('blocked','http_status',403)
    async def run(db):
        db.add(ResearchControl(id=1));scan=NewsScan(window=now);db.add(scan);await db.commit()
        report=await rapid.observe(db,scan,now,fetch,[feed]);c=await db.scalar(select(EditorialCandidate))
        assert c.state=='queued' and c.reason=='waiting_verified_sources' and c.attempts==0
        assert report['documents']==0 and report['nominated'][0]['candidate_id']==c.id
        assert all(not s.get('organization_verified') and not s['text'] for s in c.details['sources'])
        with pytest.raises(writing.StopRun,match='insufficient_independent_topic_sources'):await queue.prepare_candidate(db,c,now,{'remaining':4})
    database(run)


def test_named_recent_announcement_is_fetched_before_generic_undated_links(client):
    event=FIXTURES[2];now=datetime.fromisoformat(event['published']);calls=[]
    def fetch(url,limit):
        calls.append(url)
        return url,html(event) if url==event['url'] else ('<meta property="article:published_time" content="'+event['published']+'"><p>'+'Generic background discussion of documentation. '*30+'</p>').encode()
    async def run(db):
        db.add(ResearchControl(id=1));scan=NewsScan(window=now);db.add(scan)
        for n in range(20):
            url=f'https://openai.com/index/generic-fixture-{n}'
            db.add(NewsObservation(key=queue.fingerprint(url),url=url,feed_url='https://openai.com/news/rss.xml',first_seen_at=now,data=dict(url=url,title='Generic background article',organization='openai',language='en',published=None)))
        db.add(NewsObservation(key=queue.fingerprint(event['url']),url=event['url'],feed_url='https://openai.com/news/rss.xml',first_seen_at=now,published_at=now,data={k:event[k] for k in ['title','url','published']}|{'organization':'openai','language':'en'}))
        await db.commit();await rapid.observe(db,scan,now,fetch,[])
        assert calls[0]==event['url'] and len(calls)==12
    database(run)

@pytest.mark.parametrize('status',[403,429,503])
def test_one_failed_feed_backs_off_without_stopping_others(client,status):
    event=FIXTURES[2];now=datetime.fromisoformat(event['published'])+timedelta(hours=1);good=feed_for(event);bad=sources.FEEDS[2]
    calls=[]
    def fetch(url,limit):
        calls.append(url)
        if url==bad.url:raise sources.SourceError('blocked','http_status',status,'3600')
        return url,rss(event) if url==good.url else html(event)
    async def operation(db):
        scan=NewsScan(window=now);db.add(scan);await db.commit();r=await rapid.observe(db,scan,now,fetch,[bad,good])
        assert r['documents']==1 and r['errors'][0]['http_status']==status
        second=NewsScan(window=now+timedelta(minutes=30));db.add(second);await db.commit();r=await rapid.observe(db,second,now+timedelta(minutes=30),fetch,[bad,good])
        assert r['feed_backoff']==(0 if status==503 else 1)
        assert calls.count(bad.url)==(2 if status==503 else 1)
    database(operation)

def documents():
    event=FIXTURES[2];out=[]
    for i,(url,org,text) in enumerate([(event['url'],'openai',event['fact']+' OpenAI presented the multimodal GPT-4o model in its announcement. '+ 'The original description introduces text input and output alongside image understanding and audio interaction. '*10),
        ('https://www.microsoft.com/en-us/research/test-fixture-gpt4o','microsoft','Independent synthetic fixture about the GPT-4o announcement. '+ 'An integration document distinguishes service access, evaluation responsibilities and the need to check technical conditions before adopting a product. '*12)],1):
        out.append(dict(id=i,url=url,title=event['title'],organization=org,organization_verified=True,published=event['published'],language='en',text=text))
    return out

def test_event_identity_combines_sources_without_counting_same_publisher_twice(client):
    now=datetime.fromisoformat(FIXTURES[2]['published']);docs=documents()
    async def operation(db):
        db.add(ResearchControl(id=1));await db.commit()
        a=await queue.upsert_event(db,[docs[0]],events.identify(docs[0]),now)
        duplicate=dict(docs[0],id=3,url='https://openai.com/index/test-fixture-copy')
        b=await queue.upsert_event(db,[duplicate],events.identify(duplicate),now)
        assert a.id==b.id and b.state=='queued'
        c=await queue.upsert_event(db,[docs[1]],events.identify(docs[1]),now)
        assert c.id==a.id and c.state=='ready'
        assert c.details['decision']['evidence_organizations']==['microsoft','openai']
        c.state='published';await db.commit()
        d=await queue.upsert_event(db,[dict(docs[1],title='OpenAI introduces GPT-4o multimodal model')],events.identify(docs[1]),now)
        assert d.id==a.id and d.state=='published'
    database(operation)


def test_prolific_publisher_cannot_push_independent_evidence_out_of_catalogue(client):
    now=datetime.fromisoformat(FIXTURES[2]['published']);docs=documents()
    async def operation(db):
        db.add(ResearchControl(id=1));await db.commit()
        for n in range(10):
            doc=dict(docs[0],id=n+10,url=f'https://openai.com/index/test-fixture-{n}')
            await queue.upsert_event(db,[doc],events.identify(doc),now)
        c=await queue.upsert_event(db,[docs[1]],events.identify(docs[1]),now)
        assert c.state=='ready' and len(c.details['sources'])<=8
        assert c.details['decision']['evidence_organizations']==['microsoft','openai']
    database(operation)


def test_feed_metadata_cannot_replace_already_verified_document(client):
    now=datetime.fromisoformat(FIXTURES[2]['published']);docs=documents()
    async def operation(db):
        db.add(ResearchControl(id=1));await db.commit()
        first=await queue.upsert_event(db,docs,events.identify(docs[0]),now)
        assert first.state=='ready'
        metadata=dict(docs[0],text='',organization_verified=False)
        after=await queue.upsert_event(db,[metadata],events.identify(metadata),now)
        assert after.id==first.id and after.state=='ready'
        assert all(s['organization_verified'] and len(s['text'])>=500 for s in after.details['sources'])
    database(operation)

def context(monkeypatch):
    @asynccontextmanager
    async def maker():
        async for db in app_override()():yield db
    redis=Redis();monkeypatch.setattr(rapid,'get_sessionmaker',lambda:maker);monkeypatch.setattr(rapid,'get_redis',lambda:redis)
    return redis

def test_scan_concurrency_restart_and_flag(client,monkeypatch):
    redis=context(monkeypatch);event=FIXTURES[2];now=datetime.fromisoformat(event['published']);feed=feed_for(event);calls=[]
    def fetch(url,limit):calls.append(url);return url,rss(event) if url==feed.url else html(event)
    async def operation(db):db.add(ResearchControl(id=1,enabled=True,rapid_enabled=True))
    database(operation)
    async def run():await asyncio.gather(rapid.tick(now,fetch,[feed]),rapid.tick(now,fetch,[feed]))
    asyncio.run(run());asyncio.run(rapid.tick(now,fetch,[feed]));assert calls.count(feed.url)==1
    assert client.patch('/editorial/research',headers=AUTH,json={'enabled':True,'rapid_enabled':False}).status_code==200
    asyncio.run(rapid.tick(now+timedelta(minutes=30),fetch,[feed]));assert calls.count(feed.url)==1


def test_interrupted_free_scan_is_marked_and_next_window_recovers(client,monkeypatch):
    context(monkeypatch);now=datetime(2024,5,13,12,tzinfo=UTC)
    async def seed(db):
        db.add(ResearchControl(id=1,enabled=True,rapid_enabled=True));db.add(NewsScan(window=now-timedelta(hours=1),created_at=now-timedelta(hours=1)))
    database(seed);asyncio.run(rapid.tick(now,lambda *a:pytest.fail('Empty feed list must not fetch'),[]))
    async def check(db):
        rows=(await db.scalars(select(NewsScan).order_by(NewsScan.window))).all()
        assert [r.state for r in rows]==['interrupted','completed'] and rows[0].report['model_calls']==0
    database(check)

def test_dispatch_outside_night_and_budget_retention(client,monkeypatch):
    context(monkeypatch);now=datetime.fromisoformat(FIXTURES[2]['published']);monkeypatch.setattr(executions,'utcnow',lambda:now)
    async def seed(db):
        db.add(ResearchControl(id=1,enabled=True,rapid_enabled=True));await db.commit()
        docs=documents();await queue.upsert_event(db,docs,events.identify(docs[0]),now)
    database(seed);assert due(now,ResearchSettings()) is None
    asyncio.run(rapid.dispatch(now))
    async def check(db):
        j=await db.scalar(select(EditorialExecution));assert j.state=='queued' and j.mode=='rapid' and j.reserved_microusd==0
        assert j.report['automatically_authorized']
    database(check)
    asyncio.run(rapid.dispatch(now))
    async def count(db):assert await db.scalar(select(func.count()).select_from(EditorialExecution))==1
    database(count)

def test_priority_uses_evidence_and_named_events_not_unrelated_keywords():
    doc=documents()[0];event=events.identify(doc)
    assert event['entity']=='openai' and event['event']=='launch'
    assert events.identify(dict(doc,title='Hello GPT‑4o',text='We are announcing GPT‑4o today.'))['product']=='gpt4o'
    assert not events.identify(dict(doc,title='AI roundup',text='Generic discussion of many technologies.'))
    assert not events.identify(dict(doc,title='GPT-4o and Blackwell comparison',text='A comparison of earlier announcements.'))
    assert not events.compatible(event,events.identify(dict(doc,title='NVIDIA announces Blackwell',text='Blackwell hardware launch.')))


@pytest.mark.parametrize('title,category',[
    ('Tesla unveils Optimus robot','robotics'),('NVIDIA announces Jetson Thor','hardware'),
    ('Tesla introduces Cybercab','autonomy'),('Waymo announces driver deployment','autonomy'),
    ('OpenAI launches GPT-6.1-mini','models')])
def test_detection_covers_robotics_autonomy_hardware_and_models(title,category):
    assert events.identify({'title':title,'text':'','published':'2024-05-13T12:00:00+00:00'})['category']==category


def test_generic_robotaxi_is_not_attributed_to_tesla_and_versions_stay_distinct():
    base={'published':'2024-05-13T12:00:00+00:00','text':''}
    assert events.identify(dict(base,title='Robotaxi service launches in a city')) is None
    one=events.identify(dict(base,title='Anthropic launches Claude Sonnet 4.5'))
    two=events.identify(dict(base,title='Anthropic launches Claude Opus 4.1'))
    assert not events.compatible(one,two)
    assert events.identify(dict(base,title='NVIDIA introduces GR00T N1.5'))['category']=='robotics'
    variants=[events.identify(dict(base,title='OpenAI introduces '+name)) for name in ['GPT-6.1 Terra','GPT-6.1-Sol','GPT-4o','GPT-4o-mini']]
    assert len({v['product'] for v in variants})==4


@pytest.mark.parametrize('limit',['daily','monthly'])
def test_no_budget_preserves_ready_candidate_without_creating_paid_job(client,monkeypatch,limit):
    context(monkeypatch);now=datetime.fromisoformat(FIXTURES[2]['published'])
    async def seed(db):
        db.add(ResearchControl(id=1,enabled=True,rapid_enabled=True));await db.commit()
        docs=documents();await queue.upsert_event(db,docs,events.identify(docs[0]),now)
        db.add(ResearchRun(editorial_date=now.date() if limit=='daily' else now.date()-timedelta(days=1),reserved_microusd=150000 if limit=='daily' else 5000000))
    database(seed);asyncio.run(rapid.dispatch(now))
    async def check(db):
        c=await db.scalar(select(EditorialCandidate));assert c.state=='ready' and c.reason=='budget_exhausted' and c.attempts==0
        assert not await db.scalar(select(EditorialExecution.id))
    database(check)


def historical_draft(corpus):
    text=[
        'OpenAI presentó GPT-4o como un modelo multimodal. Su anuncio describe el trabajo con texto, imágenes y audio. Esto permite conocer el alcance anunciado, pero no equivale a una medición independiente del rendimiento. Antes de incorporarlo a una aplicación conviene revisar la documentación y las condiciones del servicio.',
        'La documentación de integración ayuda a distinguir el modelo de la forma de acceder al servicio. Hay que comprobar los formatos admitidos y las condiciones que correspondan a cada aplicación. Esta explicación no afirma haber realizado una prueba comercial ni haber obtenido resultados experimentales con el producto.',
        'El anuncio y la documentación complementaria aportan perspectivas diferentes sobre el mismo modelo. Leer ambas fuentes ayuda a separar una presentación del producto de una decisión de uso. Un equipo debe evaluar sus necesidades antes de adoptar una tecnología y conservar la referencia de los documentos que consulte.',
        'Las capacidades anunciadas no garantizan una respuesta correcta para cualquier tarea. La comprobación de los resultados sigue siendo necesaria cuando se usa un asistente. Este artículo describe información documental y no pretende sustituir una evaluación concreta sobre los datos y las necesidades de una aplicación.'
    ]
    return {'title':'GPT-4o: qué anunció OpenAI y qué conviene comprobar','slug':'fixture-gpt4o-historical-isolated',
        'summary':'Una explicación documental del anuncio multimodal y de las comprobaciones necesarias antes de utilizar un servicio en una aplicación.',
        'section':'actualidad','title_evidence':[{'fragment_id':corpus[0]['fragments'][0]['fragment_id']}],
        'summary_evidence':[{'fragment_id':corpus[0]['fragments'][0]['fragment_id']}],
        'paragraphs':[{'heading':h,'text':t,'evidence':[{'fragment_id':corpus[i%2]['fragments'][0]['fragment_id']}]} for i,(h,t) in enumerate(zip(['El alcance anunciado','La integración tiene condiciones','Dos documentos para contrastar','Qué queda por evaluar'],text))]}


def test_rapid_job_reuses_full_generation_review_publication_path_without_cost(client,monkeypatch):
    context(monkeypatch);now=datetime.fromisoformat(FIXTURES[2]['published']);docs=documents();corpus=evidence.catalogue(docs);calls=[]
    monkeypatch.setattr(executions,'utcnow',lambda:now);monkeypatch.setattr(worker,'utcnow',lambda:now)
    def provider(config,payload):
        kind=payload['text']['format']['name'];calls.append(kind)
        if kind=='groundeddraft':result=historical_draft(corpus)
        else:
            result=approved_payload(payload);result['checks']={r.pop('target_id'):r for r in result['checks']}
        return json.dumps(result),{'input_tokens':10,'output_tokens':100}
    monkeypatch.setattr(writing,'call',provider)
    async def seed(db):
        db.add(ResearchControl(id=1,enabled=True,rapid_enabled=True));await db.commit();await queue.upsert_event(db,docs,events.identify(docs[0]),now)
    database(seed);asyncio.run(rapid.dispatch(now))
    async def run(db):
        job=await db.scalar(select(EditorialExecution));redis=Redis();redis.value=b'owner'
        async def verify(snapshot,page):return {'html':True,'api':True,'seo':True,'sitemap':True,'image':True,'url':'https://test.invalid/articulos/'+snapshot['slug']}
        await executions.execute_job(db,job,ResearchSettings(),redis,b'owner',verifier=verify)
        assert job.state=='completed' and calls==['groundeddraft','groundedreview']
        assert job.reserved_microusd<=150000
        article=await db.get(Article,job.article_id);assert article.status=='published'
        assert (await db.scalar(select(EditorialCandidate))).state=='published'
    database(run)
    assert client.get('/articles/fixture-gpt4o-historical-isolated').status_code==200
    asyncio.run(rapid.dispatch(now))
    assert len(calls)==2


def test_nightly_scheduler_reuses_budget_bucket_once_after_unsuccessful_daytime_job(client,monkeypatch):
    from app.research import editorial
    now=datetime(2024,5,13,20,30,tzinfo=UTC);redis=context(monkeypatch);calls=[]
    monkeypatch.setattr(worker,'utcnow',lambda:now);monkeypatch.setattr(worker,'get_redis',lambda:redis)
    monkeypatch.setattr(worker,'get_sessionmaker',rapid.get_sessionmaker)
    monkeypatch.setattr(worker,'settings',lambda:ResearchSettings(api_key='test-not-real'))
    async def execute(db,run,config,r,t):
        calls.append(run.id);assert run.reserved_microusd==20000
        run.status='skipped';run.reason='no_viable_candidate';await db.commit()
    monkeypatch.setattr(editorial,'execute',execute)
    async def seed(db):
        db.add(ResearchControl(id=1,enabled=True,rapid_enabled=True));db.add(ResearchRun(editorial_date=now.date(),status='skipped',reason='manual_budget_bucket',reserved_microusd=20000,report={'budget_bucket':True}))
    database(seed);assert due(now,ResearchSettings())==now.date()
    asyncio.run(worker.tick());asyncio.run(worker.tick());assert len(calls)==1
