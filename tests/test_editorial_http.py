"""Real Nuxt SSR + FastAPI transport + isolated DB; no provider or production writes."""
import asyncio
import json
import re
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

import httpx
import pytest

from test_research import client,database,Redis
from test_editorial_engines import NOW,receipt,docs,no_news,provider_factory
from app.models import ResearchControl,ResearchRun,EditorialCandidate
from app.research import editorial,writing
from app.research.config import ResearchSettings
from app.research.publication import verify_html,PublicationError
from app.research.blueprints import BLUEPRINTS
from test_editorial_matrix import plan_provider
from app.research.queue import seed_evergreen
from sqlalchemy import select

pytestmark=pytest.mark.skipif(os.environ.get('FOROIA_ANALYTICS_LOCAL')!='1',reason='Requires local Nuxt build')
ROOT=Path(__file__).parents[1]


@pytest.fixture
def http_database(client,tmp_path):
    # SSR makes concurrent API reads: separate connections must not roll back the
    # writer's transaction, as happens with SQLite StaticPool's shared connection.
    from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
    from sqlalchemy.pool import NullPool
    from app.core import db as core_db
    from app.models import Base
    from app.main import app
    engine=create_async_engine('sqlite+aiosqlite:///'+(tmp_path/'editorial.db').as_posix(),poolclass=NullPool)
    maker=async_sessionmaker(engine,expire_on_commit=False)
    async def override():
        async with maker() as db:yield db
    async def setup():
        async with engine.begin() as conn:await conn.run_sync(Base.metadata.create_all)
    asyncio.run(setup())
    previous=app.dependency_overrides[core_db.get_db]
    app.dependency_overrides[core_db.get_db]=override
    yield client
    app.dependency_overrides[core_db.get_db]=previous
    asyncio.run(engine.dispose())


@pytest.mark.parametrize('blueprint',(*BLUEPRINTS,None,'official-announcement','dual-lanes','triple-lanes'),ids=lambda b:b if isinstance(b,str) else b.key if b else 'historical-nightly-web-news')
def test_real_isolated_publication_reaches_nuxt_ssr_schema_and_sitemap(http_database,tmp_path,monkeypatch,blueprint):
    official = blueprint == 'official-announcement'
    triple=blueprint=='triple-lanes'
    dual = blueprint in ('dual-lanes','triple-lanes') if isinstance(blueprint,str) else False
    if official or dual:blueprint=None
    client=http_database
    mutex=threading.Lock()
    class API(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            with mutex:response=client.get(self.path)
            with (tmp_path/'api.log').open('a',encoding='utf-8') as output:output.write(self.path+' '+str(response.status_code)+' '+response.text+'\n')
            self.send_response(response.status_code);self.send_header('Content-Type',response.headers.get('content-type','application/json'));self.end_headers()
            self.wfile.write(response.content)
    server=ThreadingHTTPServer(('127.0.0.1',0),API)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    env={**os.environ,'NITRO_HOST':'127.0.0.1','NITRO_PORT':str(port),
        'NUXT_API_BASE':f'http://127.0.0.1:{server.server_port}','NUXT_PUBLIC_SITE_URL':base,
        'NUXT_PUBLIC_ANALYTICS_ENABLED':'false','NUXT_PUBLIC_GA4_ID':'','NUXT_ADS_PUBLISHER_ID':'','NUXT_EDITORIAL_API_TOKEN':''}
    log=(tmp_path/'nuxt.log').open('w',encoding='utf-8')
    process=subprocess.Popen([os.environ['FOROIA_NODE_BINARY'],'.output/server/index.mjs'],cwd=ROOT/'web',env=env,stdout=log,stderr=log)
    calls=[]
    if blueprint:provider=plan_provider(blueprint,calls)
    else:
        from test_rapid_news import historical_draft
        from test_evidence_first import approved_payload
        def provider(config,payload):
            calls.append(payload['text']['format']['name'])
            if calls[-1] in {'newsresearch','sourcerecovery'}:
                from test_nightly_web import nomination,usage
                from test_event_sources import recovered
                item=nomination();data=usage();data['_web']['sources']=[]
                if calls[-1]=='sourcerecovery':
                    item=recovered(item)
                    if official:item['urls']=item['urls'][:1]
                else:
                    item['urls']=['https://openai.com/index/blocked-isolated-fixture']
                return json.dumps({'candidates':[item]}),data
            if calls[-1]=='evergreendraft':
                from test_editorial_engines import tutorial_payload
                value=tutorial_payload(payload)
                if triple and json.loads(payload['input'])['editorial_policy']['candidate_id']!=1:
                    value.update(title='Guardar historiales de un asistente en SQLite sin repetir registros',slug='guardar-historiales-asistente-sqlite',
                        summary='Un procedimiento para conservar registros identificados en una base de datos y actualizar sus campos de manera controlada.')
                    for p in value['paragraphs']:p['text']=p['text'].replace('respuesta','registro').replace('documento','resumen').replace('validación','persistencia').replace('comprobación','preparación')
            elif calls[-1]=='groundeddraft':
                corpus=json.loads(payload['input'])['sources']
                value=historical_draft([corpus[0],corpus[0]] if official else corpus)
                if official:
                    value.update(title='OpenAI presenta GPT-4o como modelo multimodal',summary='Según OpenAI, el anuncio describe un modelo multimodal y el alcance de sus capacidades anunciadas.')
            else:value=approved_payload(payload)
            return json.dumps(value),{'input_tokens':10,'output_tokens':100}
    monkeypatch.setattr(writing,'call',provider);monkeypatch.setattr(editorial,'utcnow',lambda:NOW)
    try:
        for _ in range(100):
            try:
                if httpx.get(base,trust_env=False).status_code==200:break
            except httpx.HTTPError:pass
            assert process.poll() is None
            time.sleep(.2)
        else:pytest.fail('Nuxt did not start')
        def getter(url):
            response=httpx.get(url,trust_env=False,timeout=20)
            if response.status_code!=200:
                (tmp_path/'http-error.txt').write_text(url+'\n'+response.text,encoding='utf-8')
            if '/sitemap' in url:
                with (tmp_path/'sitemaps.log').open('a',encoding='utf-8') as output:output.write(url+'\n'+response.text+'\n')
            if response.status_code!=200:raise PublicationError('publication_http_'+str(response.status_code),response.status_code>=500)
            return response.content if response.headers.get('content-type','').startswith('image/') else response.text
        async def verify(snapshot,page):return await asyncio.to_thread(verify_html,snapshot,base,page,getter)
        async def operation(db):
            if blueprint is None:
                from test_nightly_web import NOW as stamp,pages
                from app.research import sources
                monkeypatch.setattr(editorial,'utcnow',lambda:stamp)
                from test_event_sources import deny_unknown
                monkeypatch.setattr(sources,'fetch',deny_unknown)
                db.add(ResearchControl(id=1,enabled=True,rapid_enabled=False))
                run=ResearchRun(editorial_date=stamp.date());db.add(run);await db.commit()
                redis=Redis();redis.value=b'owner'
                if dual:
                    from app.research import lanes
                    from app.research.sources import collect
                    monkeypatch.setattr(lanes,'utcnow',lambda:stamp)
                    from app.research import worker
                    monkeypatch.setattr(worker,'utcnow',lambda:stamp)
                    await lanes.execute(db,run,ResearchSettings(api_key='offline-simulated-provider',daily_usd='.50' if triple else '.20',monthly_usd='15' if triple else '10',two_lanes=True,practical_publications=2 if triple else 1),redis,b'owner',
                        news_collector=collect,doc_loader=docs,verifier=verify,receipt_path=receipt(tmp_path,stamp))
                    assert len(run.report['publications'])==(3 if triple else 2),run.report
                    for item in run.report['publications']:
                        candidate=await db.get(EditorialCandidate,item['candidate_id'])
                        assert candidate.state=='published' and all(candidate.details['verification'][k] for k in ['api','html','seo','sitemap','image'])
                    return
                await editorial.execute(db,run,ResearchSettings(api_key='offline-simulated-provider'),redis,b'owner',verifier=verify,
                    receipt_path=receipt(tmp_path,stamp))
                assert run.status=='published' and len(run.report['publications'])==1,(run.reason,run.report.get('candidate_attempts'),run.report.get('generation_failure'))
                candidate=await db.get(EditorialCandidate,run.report['publications'][0]['candidate_id'])
                assert candidate.state=='published' and all(candidate.details['verification'][k] for k in ['api','html','seo','sitemap','image'])
                if official:
                    assert candidate.details['selection']['verification_mode']=='official_announcement'
                    from app.models import Article
                    assert len((await db.get(Article,run.article_id)).sources)==1
                assert run.report['alternative_web_research']['settled']
                assert run.report['news_discovery']['opportunities'][0]['initial_reason']=='document_inaccessible'
                return
            await seed_evergreen(db)
            candidates=(await db.scalars(select(EditorialCandidate))).all()
            next(c for c in candidates if c.details['blueprint']==blueprint.key).priority=100
            db.add(ResearchControl(id=1,enabled=True));run=ResearchRun(editorial_date=NOW.date());db.add(run);await db.commit()
            redis=Redis();redis.value=b'owner'
            await editorial.execute(db,run,ResearchSettings(),redis,b'owner',news_collector=no_news,doc_loader=docs,
                verifier=verify,receipt_path=receipt(tmp_path))
            # Exercise real restart reconciliation if initial HTTP visibility is transient.
            from contextlib import asynccontextmanager
            from app.core import db as core_db,limits
            from test_accounts_api import app_override
            candidate=await db.get(EditorialCandidate,run.report['active_candidate_id'],populate_existing=True)
            for _ in range(2):
                if candidate.state!='needs_verification':break
                candidate.next_attempt_at=None;await db.commit()
                @asynccontextmanager
                async def session():
                    async for other in app_override()():yield other
                monkeypatch.setattr(core_db,'get_sessionmaker',lambda:session)
                monkeypatch.setattr(limits,'get_redis',lambda:Redis())
                await editorial.reconcile_publications(verifier=verify)
                await db.refresh(candidate);await db.refresh(run)
            if run.reason!='quality_checks_passed':
                rows=(await db.scalars(select(EditorialCandidate).where(EditorialCandidate.attempts>0))).all()
                (tmp_path/'failure.json').write_text(json.dumps({'run':run.report,'candidates':[{'id':c.id,'state':c.state,'reason':c.reason,'details':c.details} for c in rows]},default=str),encoding='utf-8')
            assert run.status=='published' and run.reason=='quality_checks_passed',run.report
            candidate=await db.get(EditorialCandidate,run.report['active_candidate_id'])
            assert candidate.state=='published' and candidate.details['verification']['sitemap']
            html=await asyncio.to_thread(getter,base+candidate.details['verification']['url'].split(base,1)[-1])
            assert re.search(r'<h1\b',html) and 'application/ld+json' in html
            assert ('<pre' in html)==bool(blueprint.example)
        database(operation)
        items=client.get('/articles').json()['items'];assert len(items)==(3 if triple else 2 if dual else 1)
        assert len(calls)==(8 if triple else 6 if dual else 2 if blueprint else 4)
    finally:
        process.terminate();process.wait(timeout=15);log.close();server.shutdown();server.server_close()
