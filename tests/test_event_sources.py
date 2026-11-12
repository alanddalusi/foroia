"""Offline event recovery. Providers and HTML are synthetic unless a capture says otherwise."""
import json
import gzip
import base64
from datetime import datetime
from pathlib import Path
import pytest
from sqlalchemy import select,func
from test_nightly_web import client,database,seed,redis,nomination,pages,usage,NOW
from app.models import EditorialCandidate,GenerationUsage
from app.research import event_sources,night_web,sources,news_gate,writing
from app.research.config import ResearchSettings

BLOCKED='https://openai.com/index/blocked-isolated-fixture'

def recovered(item=None):
    item=item or nomination()
    return {'event_id':event_sources.event_id(night_web.NewsOpportunity.model_validate(item)),'urls':item['urls'],'reason':'Isolated recovered-source fixture'}

def nominations():return [night_web.NewsOpportunity.model_validate(dict(nomination(),urls=[BLOCKED]))]
def silent_usage():
    v=usage();v['_web']['sources']=[];return v
def deny_unknown(url,limit):
    if url in nomination()['urls']:return pages(url,limit)
    raise sources.SourceError('Blocked synthetic fixture','http_status',403)

def test_query_combines_event_company_product_and_date():
    rows=json.loads(Path('tests/fixtures/news_retry_candidates_20261029.json').read_text())['nominations']
    for row in rows[:3]:
        item=night_web.NewsOpportunity.model_validate(row);plan=event_sources.plan(item)
        assert item.date in plan['official_query'] and item.date in plan['independent_query']
        assert event_sources.entrypoints(item)
    amd=night_web.NewsOpportunity.model_validate(rows[2])
    assert 'amd' in event_sources.query(amd) and 'helios' in event_sources.query(amd)
    assert 'https://ir.amd.com/news-events/press-releases' in event_sources.entrypoints(amd)

def test_alternative_request_is_scoped_and_bounded():
    config=ResearchSettings();request=event_sources.search_payload(config,NOW,[],nominations())
    assert request['max_tool_calls']==1 and request['parallel_tool_calls'] is False
    assert request['tool_choice']=='required'
    assert request['tools'][0]['external_web_access'] is True
    assert 1<=len(request['tools'][0]['filters']['allowed_domains'])<=100
    assert all(h in sources.HOSTS for h in request['tools'][0]['filters']['allowed_domains'])
    assert event_sources.drafting_headroom(config)==40000

def test_official_index_recovers_original_after_disallowed_aggregator(client):
    item=dict(nomination(),urls=['https://unapproved-aggregator.test/story',nomination()['urls'][1]])
    index='https://openai.com/news/';original=nomination()['urls'][0]
    def fetch(url,limit):
        if url==index:return url,('<h1>News</h1><a href="'+original+'">'+item['title']+'</a>').encode()
        return pages(url,limit)
    async def operation(db):
        run=await seed(db)
        report=await night_web.discover(db,run,ResearchSettings(),redis(),b'owner',NOW,
            lambda *a:(json.dumps({'candidates':[item]}),silent_usage()),fetch,recovery_feeds=(),official_indexes=[index],
            alternative_provider=lambda *a:pytest.fail('Free recovery must avoid another model call'))
        assert report['opportunities'][0]['reason_for_decision']=='verified_queued'
        assert report['event_searches'][0]['method']=='official_index_local_query'
        assert original in report['event_searches'][0]['found_urls']
        assert 'official_statement' in {d['evidence_role'] for d in report['document_snapshots']}
    database(operation)

def test_fallback_reuses_atomic_budget_and_cached_response(client):
    calls=[]
    def alternate(config,payload):calls.append(payload);return json.dumps({'candidates':[recovered()]}),usage()
    async def operation(db):
        run=await seed(db)
        for _ in range(2):
            report=await night_web.discover(db,run,ResearchSettings(),redis(),b'owner',NOW,
                lambda *a:(json.dumps({'candidates':[n.model_dump() for n in nominations()]}),silent_usage()),
                deny_unknown,recovery_feeds=(),alternative_provider=alternate)
            assert report['opportunities'][0]['reason_for_decision']=='verified_queued'
            assert report['opportunities'][0]['initial_reason']=='document_inaccessible'
            assert report['alternative_research']['settled'] is True
        assert len(calls)==1
        assert await db.scalar(select(func.count(GenerationUsage.id)))==2
        assert await db.scalar(select(func.count(EditorialCandidate.id)))==1
        stages=(await db.scalars(select(GenerationUsage.stage))).all()
        assert sorted(stages)==['NewsResearch','SourceRecovery']
        assert run.reserved_microusd==27200
    database(operation)

@pytest.mark.parametrize('state',['calling','failed'])
def test_uncertain_alternative_is_never_repeated(client,state):
    async def operation(db):
        run=await seed(db);run.reserved_microusd=55000
        run.report={'alternative_web_research':{'state':state,'reserved_microusd':55000,'ledger_key':'a'*64}}
        await db.commit()
        found,_=await event_sources.search(db,run,ResearchSettings(),redis(),b'owner',NOW,nominations(),
            lambda *a:pytest.fail('Must not repeat an uncertain charge'))
        assert not found and run.reserved_microusd==55000
    database(operation)

def test_budget_headroom_prevents_search_starving_drafting(client):
    async def operation(db):
        run=await seed(db);run.reserved_microusd=67645;await db.commit()
        found,report=await event_sources.search(db,run,ResearchSettings(),redis(),b'owner',NOW,nominations(),
            lambda *a:pytest.fail('Search must leave room for draft/review'))
        assert not found and report['state']=='unfunded'
        assert run.reserved_microusd==67645 and 'alternative_web_research' not in run.report
    database(operation)

def test_changed_event_from_alternative_is_rejected(client):
    def alternate(*args):return json.dumps({'candidates':[dict(recovered(),event_id='event_unknown')]}),usage()
    async def operation(db):
        run=await seed(db)
        report=await night_web.discover(db,run,ResearchSettings(),redis(),b'owner',NOW,
            lambda *a:(json.dumps({'candidates':[n.model_dump() for n in nominations()]}),silent_usage()),
            deny_unknown,recovery_feeds=(),alternative_provider=alternate)
        assert report['web']['verified_candidates']==0
        assert report['alternative_research']['invalid_candidates']
        assert report['alternative_research']['reason']=='all_candidates_invalid'
    database(operation)

def test_joint_partnership_needs_both_parties_and_specific_product():
    rows=json.loads(Path('tests/fixtures/news_retry_candidates_20261029.json').read_text())['nominations']
    assert news_gate.matches(rows[2],{'title':'AMD and Meta Advance Strategic Partnership','text':'AMD Helios and EPYC power the infrastructure.'})['related']
    assert not news_gate.matches(rows[2],{'title':'AMD and TCS Announce Partnership','text':'AMD Helios infrastructure'})['related']
    assert not news_gate.matches(rows[1],{'title':'Microsoft and OpenAI expand their partnership','text':'ChatGPT and Codex'})['related']

def test_timeout_rejects_without_fetching_or_spending(client):
    async def operation(db):
        run=await seed(db)
        report=await night_web.discover(db,run,ResearchSettings(),redis(),b'owner',NOW,
            lambda *a:(json.dumps({'candidates':[nomination()]}),silent_usage()),
            lambda *a:pytest.fail('No fetch after deadline'),recovery_feeds=(),time_budget_seconds=0,
            alternative_provider=lambda *a:pytest.fail('No search after deadline'))
        assert report['alternative_research']['reason']=='recovery_timeout'
        assert report['statistics']['fetch_counts']=={'article':0,'index':0,'feed':0}
    database(operation)

@pytest.mark.parametrize('clock',['original_run','fresh_capture'])
def test_latest_five_candidates_find_original_amd_from_real_captured_indexes(client,clock):
    """Fresh HTTP bytes replayed at the original run clock, not a historical capture."""
    from app.models import Article
    from test_articles_api import article
    recorded=json.loads(Path('tests/fixtures/news_retry_candidates_20261029.json').read_text())
    capture=json.loads(gzip.decompress(Path('tests/fixtures/event_http_capture_20261029.json.gz').read_bytes()))
    saved={sources.canonical(r['requested_url']):r for r in capture['rows'] if sources.urlsplit(r['requested_url']).hostname in sources.HOSTS}
    stamp=datetime.fromisoformat('2026-10-29T09:32:50+00:00' if clock=='original_run' else capture['rows'][0]['captured_at'])
    def fetch(url,limit):
        row=saved.get(url)
        if row is None:raise sources.SourceError('Not captured, not inferred','offline_not_captured')
        if row.get('error'):raise sources.SourceError('Recorded transport result',row['error'],row.get('http_status'))
        return row['final_url'],base64.b64decode(row['body_base64'])
    async def original(*args):return [night_web.NewsOpportunity.model_validate(n) for n in recorded['nominations']],{}
    async def operation(db):
        from app.research.news_recovery import discover
        run=await seed(db)
        db.add(Article(**{**article(),'title':'Anthropic files its Form S-1 for IPO','slug':'existing-anthropic-filing','sources':[]},status='published',published_at=stamp))
        await db.commit()
        report=await discover(db,run,ResearchSettings(),redis(),b'owner',stamp,
            fetcher=fetch,recovery_feeds=(),research_fn=original,official_indexes=event_sources.entrypoints)
        amd=next(d for d in report['opportunities'] if d['title']==recorded['nominations'][2]['title'])
        assert len(amd['verified_source_urls'])==(1 if clock=='original_run' else 0),amd['diagnostics']
        assert all(sources.urlsplit(u).hostname in {'ir.amd.com','newsroom.amd.com'} for u in amd['verified_source_urls'])
        assert amd['reason_for_decision']==('verified_queued' if clock=='original_run' else 'document_stale')
        assert report['web']['verified_candidates']==(1 if clock=='original_run' else 0)
        assert any(s.get('found_urls') for s in report['event_searches'])
        assert report['opportunities'][3]['reason_for_decision']=='already_published'
        assert all(d['organization']=='amd' for d in report['document_snapshots'])
    database(operation)

def test_original_amd_date_and_same_organization_are_preserved():
    capture=json.loads(gzip.decompress(Path('tests/fixtures/event_http_capture_20261029.json.gz').read_bytes()))
    rows=[r for r in capture['rows'] if '/detail/1302/' in r['requested_url']]
    assert len(rows)==1
    body=base64.b64decode(rows[0]['body_base64'])
    assert sources.publication_stamp(body,rows[0]['final_url'])==(datetime.fromisoformat('2026-10-27T13:20:00+00:00'),'instant')

def test_nested_history_remains_private():
    from app.research.routes import report_view
    view=report_view({'prior_attempts':[{'report':{'alternative_web_research':{'raw':'private provider text','usage':{'x':1}},'news_discovery':{'document_snapshots':[{'text':'private source body'}]}}}]})
    assert 'private' not in json.dumps(view)

@pytest.mark.parametrize('mode',['invalid_json','no_search','unsafe_domain','same_organization'])
def test_bad_alternatives_never_reach_generation_or_repeat_calls(client,mode):
    calls=[]
    def alternate(config,payload):
        calls.append(1);data=usage();row=recovered()
        if mode=='no_search':data['_web']['search_calls']=0
        if mode=='unsafe_domain':row['urls']=['https://127.0.0.1/private']
        if mode=='same_organization':row['urls']=[nomination()['urls'][0],'https://openai.com/index/same-org-isolated-fixture']
        return ('not valid JSON' if mode=='invalid_json' else json.dumps({'candidates':[row]})),data
    def fetch(url,limit):
        if url.endswith('/same-org-isolated-fixture'):
            _,body=pages(nomination()['urls'][1],limit);return url,body
        return deny_unknown(url,limit)
    async def operation(db):
        run=await seed(db)
        for _ in range(2):
            report=await night_web.discover(db,run,ResearchSettings(),redis(),b'owner',NOW,
                lambda *a:(json.dumps({'candidates':[dict(n.model_dump(),event=n.event+' Objective comparison.') if mode=='same_organization' else n.model_dump() for n in nominations()]}),silent_usage()),
                fetch,recovery_feeds=(),alternative_provider=alternate)
            assert report['web']['verified_candidates']==0
            assert await db.scalar(select(func.count(EditorialCandidate.id)))==0
        assert calls==[1]
    database(operation)

def test_new_official_host_still_rejects_private_dns(monkeypatch):
    import socket
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))])
    with pytest.raises(sources.SourceError):sources.fetch('https://ir.amd.com/news-events/press-releases')
