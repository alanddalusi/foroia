"""Dual-engine coordinator with a real provider adapter and no paid/network calls."""
import asyncio
import copy
from datetime import UTC,datetime,timedelta
import importlib.util
import json
from pathlib import Path

import pytest
from sqlalchemy import select,func

from test_research import EVIDENCE,Redis,client,database,review
from test_accounts_api import account_client,seed_user,session
from test_evidence_first import grounded,approved_payload
from app.research.blueprints import BLUEPRINTS
from app.models import Article,EditorialCandidate,SourceCache,GenerationUsage,ResearchRun,ResearchControl,utcnow
from app.research import editorial,writing,evidence,queue
from app.research.config import ResearchSettings
from app.research.examples import EXAMPLES,example_hash,verified_example
from app.research.documents import official_document
from app.research.publication import verify_candidate,PublicationError,article_snapshot

NOW=datetime(2026,10,24,18,tzinfo=UTC)


def receipt(tmp_path,now=NOW):
    path=tmp_path/'verified.json'
    path.write_text(json.dumps({'verified_at':now.isoformat(),'image_id':'sha256:'+'a'*64,
        'examples':{k:{'sha256':example_hash(k),'status':'passed'} for k in EXAMPLES}}))
    return str(path)


async def docs(db,url,now,budget):
    from app.research.sources import DOCUMENT_HOSTS
    from urllib.parse import urlsplit
    return {'id':int(evidence.digest(url)[:12],16),'url':url,'title':'JSON, validation and structured data',
        'language':'en','organization':DOCUMENT_HOSTS[urlsplit(url).hostname],'organization_verified':True,
        'published':None,'kind':'official_documentation','retrieved_at':now.isoformat(),
        'text':('JSON documents can be deserialized into Python objects. Invalid data raises an error. '
                'Input size and data types should be checked before processing untrusted content. '
                'A dictionary contains keys and values. Validation of syntax does not establish factual accuracy. ')*8}


def tutorial_payload(payload):
    data=json.loads(payload['input']);source=data['sources'][0];fid=source['fragments'][0]['fragment_id']
    text=('Una respuesta estructurada necesita una comprobación antes de incorporarse a otra tarea. '
        'El formato permite organizar campos, pero eso no demuestra que los datos sean correctos. '
        'Conviene separar la lectura del documento, la comprobación de tipos y la revisión de sus afirmaciones. '
        'El ejemplo adjunto ilustra esa separación con entradas acotadas y errores reconocibles. ')
    policy=data['editorial_policy']
    refs=[{'fragment_id':fid}]
    return {'title':'Validar respuestas JSON antes de utilizarlas con Python','slug':'validar-respuestas-json-python',
        'summary':'Un procedimiento para comprobar la estructura de respuestas JSON, distinguir errores de formato y reconocer sus límites.',
        'section':'programacion','title_evidence':refs,'summary_evidence':refs,
        'example_ids':[policy['example']['id']] if policy.get('example') else [],
        'paragraphs':[{'heading':h,'text':t,'evidence':refs} for h,t in zip(['Qué se comprueba','Preparar la entrada','Interpretar el resultado','Límites de la validación'],[
            text,
            'La entrada debe acotarse antes de intentar convertirla en objetos de Python. Un documento demasiado grande puede consumir recursos aunque su formato sea válido. Por eso interesa separar el control de tamaño de la lectura y decidir qué tipos de datos acepta la aplicación. El ejemplo utiliza datos de prueba y no llama a un proveedor externo de IA.',
            'Una conversión correcta indica que el documento tiene una sintaxis reconocible. Todavía hace falta contrastar los campos y sus tipos con lo que espera el siguiente paso del proceso. Esta distinción permite devolver un error concreto al encontrar una entrada inesperada, en lugar de tratarla como una respuesta utilizable sin comprobaciones.',
            'El procedimiento comprueba la estructura, no la verdad de las afirmaciones que contiene una respuesta de IA. Las entradas de prueba ayudan a observar errores reproducibles, pero no sustituyen la verificación de fuentes del contenido. Cada aplicación debe definir además qué información está autorizada a conservar y qué debe rechazar.'
        ])]}


async def no_news(now,urls):return [],{'candidate_count':0,'fetch_failures':0}
async def verifier(snapshot,page):return {'url':'https://foroiaaldia.com/articulos/'+snapshot['slug'],'html':True,'api':True,'seo':True,'sitemap':True,'image':True}


def provider_factory(calls,mode='valid',news=None):
    def provider(config,payload):
        kind=payload['text']['format']['name'];data=json.loads(payload['input']);engine=data.get('editorial_policy',{}).get('kind')
        calls.append((kind,engine))
        if mode=='provider_error':raise writing.StopRun('provider_unavailable')
        if kind=='evergreendraft':value=tutorial_payload(payload)
        elif kind=='groundeddraft':value=grounded(evidence.catalogue(news)).model_dump()
        else:
            value=approved_payload(payload)
            if kind=='updatereview':
                value.update(meaningful_change=True,changed_evidence=[{'fragment_id':data['sources'][0]['fragments'][0]['fragment_id']}])
            if mode=='news_rejected' and engine=='news':value['approved']=False;value['reasons']=['No aporta valor suficiente.']
        return json.dumps(value),{'input_tokens':100,'output_tokens':200,'input_tokens_details':{'cached_tokens':10}}
    return provider


@pytest.mark.parametrize('mode',['valid','news_valid','news_rejected','provider_error'])
def test_daily_fallback_ledger_and_publication(client,tmp_path,monkeypatch,mode):
    monkeypatch.setattr(editorial,'utcnow',lambda:NOW)
    calls=[];news=[dict(s,published=NOW.isoformat()) for s in copy.deepcopy(EVIDENCE)]
    monkeypatch.setattr(writing,'call',provider_factory(calls,mode,news))
    async def news_collector(now,urls):return news,{'candidate_count':2,'fetch_failures':0}
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True));run=ResearchRun(editorial_date=NOW.date());db.add(run);await db.commit()
        redis=Redis();redis.value=b'owner'
        await editorial.execute(db,run,ResearchSettings(),redis,b'owner',news_collector=news_collector if mode in {'news_rejected','news_valid'} else no_news,
            doc_loader=docs,verifier=verifier,receipt_path=receipt(tmp_path))
        rows=(await db.scalars(select(EditorialCandidate))).all()
        assert len(rows)>=11 and run.reserved_microusd<=150000
        if mode=='provider_error':
            assert run.reason=='provider_unavailable' and len(calls)==1
            assert (await db.scalars(select(Article))).all()==[]
            assert sum(c.details.get('unreported_usage_calls',0) for c in rows)==1
        else:
            assert run.status=='published'
            candidate=next(c for c in rows if c.state=='published')
            assert candidate.engine==('news' if mode=='news_valid' else 'evergreen') and candidate.article_id==run.article_id
            article=await db.get(Article,run.article_id)
            assert ('```python' in article.body)==(mode!='news_valid')
            assert '](/'+candidate.section+')' in article.body and len(article.sources)==(2 if mode=='news_valid' else 1)
            usage=(await db.scalars(select(GenerationUsage))).all()
            assert len(usage)==len(calls) and all(r.input_tokens==100 and r.output_tokens==200 and r.cached_tokens==10 for r in usage)
            assert sum(r.estimated_microusd for r in usage)<=run.reserved_microusd
            if mode=='news_rejected':assert any(c.engine=='news' and c.reason=='review_rejected' for c in rows)
    database(operation)
    assert len(client.get('/articles').json()['items'])==(0 if mode=='provider_error' else 1)


def test_official_single_source_allowed_but_news_still_requires_independence(client,tmp_path):
    async def operation(db):
        await queue.seed_evergreen(db)
        candidate=await db.scalar(select(EditorialCandidate).where(EditorialCandidate.keyword=='validar json ia python'))
        chosen,policy=await queue.prepare_candidate(db,candidate,NOW,{'remaining':4},doc_loader=docs,receipt_path=receipt(tmp_path))
        assert len(chosen)==1 and policy['min_organizations']==1 and policy['example']['id']=='json_validation'
        assert candidate.state=='ready'
        await queue.seed_evergreen(db)
        assert await db.scalar(select(func.count()).select_from(EditorialCandidate))==len(BLUEPRINTS)
    database(operation)


def test_source_cache_avoids_network_and_negative_cache_preserves_403(client):
    calls=[]
    def fetch(url):calls.append(url);return url,b'<main>'+b'Official JSON validation context. '*30+b'</main>'
    async def operation(db):
        url='https://docs.python.org/3.12/library/json.html'
        budget={'remaining':1}
        one=await official_document(db,url,NOW,budget,fetch)
        two=await official_document(db,url,NOW,budget,fetch)
        assert one['id']==two['id'] and two['cache_hit'] and len(calls)==1 and budget['remaining']==0
        assert one['published'] is None and one['date_kind']=='retrieved'
        from app.research.sources import SourceError
        def blocked(url):calls.append(url);raise SourceError('blocked','http_status',403)
        blocked_url='https://fastapi.tiangolo.com/tutorial/body/'
        for _ in range(2):
            with pytest.raises(SourceError) as exc:await official_document(db,blocked_url,NOW,{'remaining':1},blocked)
            assert exc.value.http_status==403
        assert calls.count(blocked_url)==1
    database(operation)


@pytest.mark.parametrize('mode',['expired','tampered','failed'])
def test_code_receipt_must_match_recent_tested_code(tmp_path,mode):
    path=Path(receipt(tmp_path,NOW-timedelta(days=3) if mode=='expired' else NOW))
    data=json.loads(path.read_text())
    if mode=='tampered':data['examples']['json_validation']['sha256']='0'*64
    if mode=='failed':data['examples']['json_validation']['status']='failed'
    path.write_text(json.dumps(data))
    assert verified_example('json_validation',path,NOW) is None


def test_sandbox_command_has_no_network_secrets_or_writable_root():
    spec=importlib.util.spec_from_file_location('runner',Path(__file__).parents[1]/'scripts/verify_editorial_examples.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    from app.research import examples
    commands=[]
    def fake(cmd,**kwargs):
        from types import SimpleNamespace
        commands.append(cmd)
        assert cmd[cmd.index('--network')+1]=='none' and '--read-only' in cmd
        assert '--cap-drop' in cmd and '--memory' in cmd and '--pids-limit' in cmd
        assert '-e' not in cmd and '--env-file' not in cmd and '-v' not in cmd
        return SimpleNamespace(returncode=0,stdout=b'OK\n')
    value=module.verify('sha256:'+'a'*64,examples,fake)
    assert len(commands)==6 and all(r['status']=='passed' for r in value['examples'].values())


def test_postpublication_critical_failure_archives_only_own_unchanged_article(client):
    from test_articles_api import article as payload
    async def operation(db):
        article=Article(**payload(),status='published',published_at=NOW);db.add(article);await db.flush()
        row=EditorialCandidate(fingerprint='a'*64,engine='evergreen',kind='guide',topic='Topic',section='tutoriales',intent='Intent',keyword='Keyword',
            state='needs_verification',article_id=article.id,details={'publication_snapshot':article_snapshot(article)})
        db.add(row);await db.commit()
        async def fail(snapshot,page):raise PublicationError('publication_missing_sitemap')
        assert not await verify_candidate(db,row,fail,NOW)
        assert article.status=='archived' and row.reason=='publication_check_failed'
    database(operation)
    assert client.get('/articles').json()['items']==[]


def test_editorial_queue_and_search_signal_import_require_editor_csrf(account_client,monkeypatch):
    from app.research import routes
    monkeypatch.setattr(routes,'get_redis',lambda:Redis())
    assert account_client.get('/editorial/research').status_code==401
    seed_user(role='member')
    assert account_client.get('/editorial/research',headers=session(account_client)).status_code==403
    seed_user('editor@example.test',role='editor');headers=session(account_client,'editor@example.test')
    async def seed(db):db.add(ResearchControl(id=1,enabled=True));await queue.seed_evergreen(db)
    database(seed)
    result=account_client.get('/editorial/research',headers=headers).json()
    assert len(result["queue"])==len(BLUEPRINTS) and result['next_execution'] and not result['reported_usage']['billing_verified']
    body={'source':'search_console_export','signals':[{'query':'validar json ia python','impressions':1200,'clicks':30,'position':12.5}]}
    assert account_client.post('/editorial/research/signals',headers={'Cookie':headers['Cookie']},json=body).status_code==403
    assert account_client.post('/editorial/research/signals',headers=headers,json=body).json()['matched']>=1
