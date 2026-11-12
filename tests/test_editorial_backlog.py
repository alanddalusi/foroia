"""Explicit one-day batch authorization; existing pipeline and money gates."""
import copy,json
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from test_research import client,database,draft,EVIDENCE,Redis,review
from test_articles_api import AUTH
from test_evidence_first import approved_payload,grounded
from app.models import Article,EditorialCandidate,EditorialExecution,ResearchRun,ResearchControl,GenerationUsage,AuditLog,utcnow
from app.research import quota,writing,evidence,executions,worker,queue
from app.research.config import ResearchSettings,MADRID
from app.research.draft_recovery import saved_draft_matches


def candidate(key,**kw):
    return EditorialCandidate(fingerprint=key,engine=kw.pop('engine','evergreen'),kind='guide',topic=key,section='programacion',intent='Understand documented API behavior',keyword=key,details=kw.pop('details',{}),**kw)


@pytest.mark.parametrize('mode',['ordinary','valid','expired','outsider','news'])
def test_batch_permit_is_bound_to_manual_execution_candidate_engine_and_day(client,mode):
    async def operation(db):
        now=utcnow();db.add(ResearchControl(id=1,enabled=True))
        for i in range(2):
            a=Article(slug=f'published-{i}',title='Published article',summary='A documented article summary.',body='Public content',section='programacion',author_name='Editor',sources=[],status='published',published_at=now)
            db.add(a);await db.flush();db.add(candidate(f'old-{i}',article_id=a.id,state='published',published_at=now,engine='news' if mode=='news' else 'evergreen'))
        c=candidate('next',state='ready',engine='news' if mode=='news' else 'evergreen');db.add(c);await db.flush()
        day=now.astimezone(MADRID).date()-(timedelta(days=1) if mode=='expired' else timedelta(0))
        audit=AuditLog(actor='editor',action='editorial_backlog_authorized',entity_type='research',entity_id=1,details={'editorial_date':str(day),'candidate_ids':[c.id+99 if mode=='outsider' else c.id],'maximum_publications':1})
        db.add(audit);await db.flush()
        job=EditorialExecution(candidate_id=c.id,prepared={'backlog_authorization_id':audit.id})
        await db.commit()
        if mode=='valid':
            await quota.check_quota(db,ResearchSettings(two_lanes=True,practical_publications=2),c,now,job)
            bucket=ResearchRun(editorial_date=now.date(),reserved_microusd=499999);db.add(bucket);await db.flush()
            job.mode='auto';job.request_key='quota-budget-exception';job.max_reserved_microusd=150000;job.reserved_microusd=0;job.report={}
            db.add(job);await db.commit()
            with pytest.raises(writing.StopRun,match='budget_exhausted'):
                await worker.reserve(db,executions.Context(job,bucket),ResearchSettings(two_lanes=True,daily_usd='.50',monthly_usd='15'),2)
        else:
            with pytest.raises(writing.StopRun,match='daily_publication_limit'):
                await quota.check_quota(db,ResearchSettings(two_lanes=True,practical_publications=2),c,now,None if mode=='ordinary' else job)
    database(operation)


def test_batch_authorization_requires_authenticated_existing_practical_candidates(client,monkeypatch):
    async def no_limit(*args):pass
    monkeypatch.setattr('app.core.limits.limit',no_limit)
    async def seed(db):
        db.add(ResearchControl(id=1,enabled=True));db.add(candidate('practical',state='ready'));db.add(candidate('news',state='ready',engine='news'))
    database(seed)
    body={'mode':'auto','candidate_id':1,'request_key':'explicit-backlog-12345','backlog_candidate_ids':[1]}
    assert client.post('/editorial/research/executions',json=body).status_code==401
    invalid=dict(body,backlog_candidate_ids=[1,2])
    assert client.post('/editorial/research/executions',json=invalid,headers=AUTH).status_code==422
    good=client.post('/editorial/research/executions',json=body,headers=AUTH)
    assert good.status_code==200 and good.json()['backlog_authorization_id']
    repeat=client.post('/editorial/research/executions',json=body,headers=AUTH)
    assert repeat.json()['id']==good.json()['id']


@pytest.mark.parametrize('tamper',[False,True])
def test_footer_compatibility_does_not_accept_a_prose_edit(tamper):
    d=draft();policy={'kind':'guide','min_organizations':2,'internal_links':[('More guides','/programacion')]}
    saved={'proposal':d.model_dump(mode='json'),'evidence_catalogue':evidence.catalogue(EVIDENCE)}
    data=writing.validate_draft(d,saved['evidence_catalogue'],[],policy,provisional=True).model_dump(mode='json')
    data['body']=data['body'].replace('\n\n## Para seguir aprendiendo\n\n- [More guides](/programacion)','\n\n[More guides](/programacion)')
    if tamper:data['body']=data['body'].replace('El anuncio','Otro anuncio',1)
    assert saved_draft_matches(SimpleNamespace(**data),saved,policy)==(not tamper)


def test_correction_quote_matches_actual_first_request_and_keeps_same_article(client,monkeypatch):
    corpus=evidence.catalogue(EVIDENCE);calls=[]
    def provider(config,payload):
        kind=payload['text']['format']['name'];calls.append(kind);data=json.loads(payload['input'])
        if kind=='evergreendraft':
            assert 'editing_plan' in data['errors']
            return json.dumps(dict(grounded(data['sources']).model_dump(mode='json'),example_ids=[])),{'input_tokens':100,'output_tokens':1000}
        return json.dumps(approved_payload(payload)),{'input_tokens':100,'output_tokens':1000}
    monkeypatch.setattr(writing,'call',provider)
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True))
        policy={'kind':'guide','min_organizations':1,'internal_links':[('More guides','/tutoriales')]}
        old=draft();payload=writing.validate_draft(old,corpus,[],policy,provisional=True).model_dump(mode='json')
        a=Article(**payload,status='draft');a.body=a.body.replace('\n\n## Para seguir aprendiendo\n\n- [More guides](/tutoriales)','\n\n[More guides](/tutoriales)');db.add(a);await db.flush()
        c=candidate('JSON schema review',state='technical_error',reason='article_changed',article_id=a.id,attempts=1,details={'blueprint':'structured-output','resume_report':{'proposal':old.model_dump(mode='json'),'evidence':old.model_dump(mode='json'),'policy':policy,'evidence_catalogue':corpus,'review':review(False).model_dump(),'corrections_used':1}})
        db.add(c);await db.flush();j=EditorialExecution(mode='correction',request_key='correction-backlog-1234',candidate_id=c.id,report={},prepared={});db.add(j);await db.commit()
        async def docs(db,url,now,budget):
            return dict(EVIDENCE[0 if 'python' in url else 1],url=url,organization='python' if 'python' in url else 'openai',kind='official_documentation',retrieved_at=now.isoformat())
        cfg=ResearchSettings(two_lanes=True,daily_usd='.50',monthly_usd='15')
        await executions.prepare_job(db,j,cfg,doc_loader=docs)
        assert j.state=='awaiting_approval',j.reason
        assert j.prepared['first_stage']=='correction' and j.max_reserved_microusd<=150000 and not calls
        j.state='queued';await db.commit();r=Redis();r.value=b'owner'
        async def verify(*args):return {'html':True,'api':True,'seo':True,'sitemap':True,'image':True,'url':'https://foroiaaldia.com/articulos/'+a.slug}
        await executions.execute_job(db,j,cfg,r,b'owner',verifier=verify)
        assert j.state=='completed' and j.article_id==a.id
        assert calls==['evergreendraft','groundedreview']
        assert j.report['corrections_used']==2 and c.attempts==1
        assert j.report['reservation_settled'] and j.reserved_microusd<j.max_reserved_microusd
    database(operation)


@pytest.mark.parametrize('mode',['valid','failed_known','unknown','wrong_usage'])
def test_manual_settlement_is_idempotent_and_never_releases_unknown_cost(client,mode):
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True));r=ResearchRun(editorial_date=utcnow().date(),reserved_microusd=1200);db.add(r);await db.flush()
        j=EditorialExecution(mode='resume',request_key='settle-backlog-1234',state='failed' if mode=='failed_known' else 'completed',run_id=r.id,reserved_microusd=1000,report={},prepared={});db.add(j);await db.flush()
        entry={'execution_id':j.id,'state':'calling' if mode=='unknown' else 'response','stage':'Review','ledger_key':'backlog-ledger','maximum_microusd':1000,'usage':{'input_tokens':10,'output_tokens':10}}
        j.report={'reserved_calls':1,'stage_checkpoints':{'hash':entry,'historical':{'execution_id':j.id+1,'state':'response','maximum_microusd':999999}}}
        db.add(GenerationUsage(run_id=r.id,request_key='backlog-ledger',stage='Review',model='gpt-5-mini',input_tokens=11 if mode=='wrong_usage' else 10,output_tokens=10,cached_tokens=0,estimated_microusd=20));await db.commit()
        for _ in range(2):await executions.settle_execution(db,j)
        await db.refresh(r);await db.refresh(j)
        assert r.reserved_microusd==(220 if mode in {'valid','failed_known'} else 1200)
        assert j.reserved_microusd==(20 if mode in {'valid','failed_known'} else 1000)
    database(operation)


def test_official_manual_can_be_focused_after_initial_18k():
    from app.research.documents import document_text
    raw=('<main>'+('Introduction '*3000)+'<p>Use str.casefold() for caseless matching. '+('Documented details. '*40)+'</p></main>').encode()
    text=document_text(raw)
    assert text.index('casefold')>18000
    focused=queue.example_focused({'text':text,'url':'https://docs.python.org/3.12/library/stdtypes.html'},['casefold'])
    assert 'casefold' in focused['text'] and len(focused['text'])<10000


def test_sqlite3_module_identifier_is_not_a_numeric_quantity_or_evidence_for_one():
    assert writing.factual_numbers('Usa sqlite3; SQLite3.connect guarda 3 filas y recibe un 429.')==['3','429']
    assert not writing.supported_number('3','import sqlite3; sqlite3.connect()')
    assert writing.supported_number('3','El límite documentado es 3 registros.')
    assert writing.factual_numbers('GPT-5.4 cuesta 3.20 USD por 1000 tokens.')==['5.4','3.20','1000']
