"""Recorded failures replayed offline; numeric pointer repairs are simulated."""
import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from test_research import client, database
from app.models import Article, EditorialCandidate
from app.research import writing, evidence, recovery, queue
from app.research.config import ResearchSettings
from app.research.documents import official_document, documentation_url

SAVED=json.loads((Path(__file__).parent/'fixtures/numeric_review_failures_20261108.json').read_text(encoding='utf-8'))
NOW=datetime(2026,11,8,4,tzinfo=UTC)


def corrected_review(case):
    policy=dict(case['policy'],numeric_citation_version=2)
    draft=writing.Draft.model_validate(case['proposal'])
    _,data,payload,*_=writing.prepare_request(ResearchSettings(),writing.Review,writing.REVIEW_INSTRUCTIONS,
        {'draft':draft.model_dump(),'sources':case['sources'],'editorial_policy':policy})
    old={c['target_id']:c for c in case['review']['checks']}
    checks=[]
    for t in data['targets']:
        key=t['target_id']
        if t.get('required_numeric_token'):
            enum=payload['text']['format']['schema']['properties']['checks']['properties'][key]['properties']['fragment_ids']['items']['enum']
            checks.append({'target_id':key,'supported':True,'fragment_ids':enum[:1]})
        else:checks.append(old[key])
    return draft,writing.GroundedReview.model_validate(dict(case['review'],checks=checks)),policy,payload


@pytest.mark.parametrize('value,expected',[
    ('HTTP 4xx y 5XX, con errores 402, 429 y 529.',['4xx','5xx','402','429','529']),
    ('Recomendamos: (1) esperar; (2) registrar; (3) comprobar. 20 intentos.',['20']),
    ('1) revisar. 2) comprobar.',[]),
    ('Un valor (20) y otro (30) deben acreditarse.',['20','30']),
])
def test_numeric_tokens_keep_http_families_and_exclude_only_ordered_labels(value,expected):
    assert writing.factual_numbers(value)==expected


def test_numeric_matching_never_accepts_substrings_or_infers_http_classes():
    assert not writing.supported_number('4','4xx')
    assert not writing.supported_number('4xx','400 401 403 429')
    assert writing.supported_number('4xx','Errors in the 4XX class')
    assert not writing.supported_number('11','119')
    assert writing.supported_number('1.000','1000')


@pytest.mark.parametrize('case',SAVED['cases'],ids=['rate-limits','errors'])
def test_real_failures_require_better_citations_not_a_new_draft(case):
    draft=writing.Draft.model_validate(case['proposal'])
    bound,meta=writing.bind_reviewed_evidence(draft,writing.GroundedReview.model_validate(case['review']),case['sources'],case['policy'])
    with pytest.raises(writing.StopRun,match='unsupported_number'):
        writing.validate_draft(bound,case['sources'],[],case['policy'],metadata_refs=meta)
    draft,verdict,policy,_=corrected_review(case)
    bound,meta=writing.bind_reviewed_evidence(draft,verdict,case['sources'],policy)
    article=writing.validate_draft(bound,case['sources'],[],policy,metadata_refs=meta)
    assert article.slug==draft.slug
    assert [p.text for p in bound.paragraphs]==[p.text for p in draft.paragraphs]
    assert all(str(s.url).startswith('https://') for s in article.sources)


def test_decoder_and_backend_both_require_numeric_fragment_not_just_approval():
    case=SAVED['cases'][0];draft,review,policy,payload=corrected_review(case)
    target=next(c for c in review.checks if '.number' in c.target_id)
    allowed=payload['text']['format']['schema']['properties']['checks']['properties'][target.target_id]['properties']['fragment_ids']['items']['enum']
    target.fragment_ids=[next(fid for fid,(_,f) in evidence.index(case['sources']).items() if not writing.supported_number('429',f['text']))]
    assert target.fragment_ids[0] not in allowed
    with pytest.raises(writing.StopRun,match='invalid_numeric_citation'):
        writing.bind_reviewed_evidence(draft,review,case['sources'],policy)


def test_invented_number_is_rejected_before_any_review_request():
    case=SAVED['cases'][0];draft=copy.deepcopy(case['proposal']);draft['paragraphs'][0]['text']+=' Obtiene un 987654321 por ciento.'
    with pytest.raises(writing.StopRun,match='unsupported_number'):
        writing.prepare_request(ResearchSettings(),writing.Review,writing.REVIEW_INSTRUCTIONS,
            {'draft':draft,'sources':case['sources'],'editorial_policy':dict(case['policy'],numeric_citation_version=2)})


def test_google_markdown_alias_uses_one_bounded_download_and_cache(client):
    calls=[]
    def fetch(url):
        calls.append(url)
        assert url=='https://aistudio.google.com/docs/tokens.md'
        return url,b'# Count tokens\n'+b'Official documentation explaining token counting and request limits. '*25
    async def operation(db):
        budget={'remaining':1}
        first=await official_document(db,'https://aistudio.google.com/docs/tokens',NOW,budget,fetch)
        again=await official_document(db,'https://ai.google.dev/gemini-api/docs/tokens',NOW,budget,fetch)
        assert first['url'].endswith('/tokens.md') and again['cache_hit']
        assert len(calls)==1 and budget['remaining']==0
    database(operation)
    assert documentation_url('https://aistudio.google.com/docs/not-a-curated-page').endswith('not-a-curated-page')


def test_retrieval_capacity_does_not_permanently_reject_candidate(client):
    async def operation(db):
        c=EditorialCandidate(fingerprint='capacity',engine='evergreen',kind='guide',topic='A useful guide',section='tutoriales',intent='A useful documented task',keyword='useful task',details={})
        db.add(c);await db.commit()
        for _ in range(6):await queue.defer_or_reject(db,c,'document_fetch_budget',NOW)
        assert c.state=='deferred' and c.attempts==0 and c.details.get('preflight_failures',0)==0
    database(operation)


@pytest.mark.parametrize('tampered',[False,True])
def test_legacy_numeric_recovery_only_queues_review_preserving_attempts(client,tampered):
    case=SAVED['cases'][0]
    async def operation(db):
        d=writing.Draft.model_validate(case['persisted_proposal'])
        data=writing.validate_draft(d,case['sources'],[],case['policy'],provisional=True)
        a=Article(**data.model_dump(mode='json'),status='draft');db.add(a);await db.flush()
        saved=dict(proposal=case['proposal'],evidence=case['persisted_proposal'],policy=case['policy'],evidence_catalogue=case['sources'],review=case['review'],corrections_used=2)
        c=EditorialCandidate(fingerprint='numeric',engine='evergreen',kind='comparison',topic='Rate limit errors',section='programacion',intent='Interpret API errors',keyword='rate limits',state='rejected',reason='unsupported_number',article_id=a.id,attempts=1,details={'resume_report':saved})
        db.add(c);await db.commit()
        if tampered:a.body+=' Changed by an editor.';await db.commit()
        changed=await recovery.recover_numeric_reviews(db,NOW)
        assert changed==(0 if tampered else 1)
        if not tampered:
            assert c.details['resume_report']['pending_review'] and not c.details['resume_report']['resume_correction']
            assert c.details['resume_report']['policy']['numeric_citation_version']==2
            assert c.details['resume_report']['corrections_used']==2 and c.attempts==1
            assert await recovery.recover_numeric_reviews(db,NOW)==0
    database(operation)


@pytest.mark.parametrize('case',SAVED['cases'],ids=['rate-limits','errors'])
def test_saved_draft_can_complete_real_worker_and_public_check_offline(client,monkeypatch,case):
    from app.models import ResearchControl,ResearchRun
    from test_research import Redis
    from test_editorial_recoverable import getter_for
    from app.research import worker
    from app.research.publication import verify_candidate,verify_html
    draft,verdict,policy,_=corrected_review(case)
    calls=[]
    def provider(config,payload):
        assert payload['text']['format']['name']=='groundedreview'
        calls.append('Review')
        return verdict.model_dump_json(),{'input_tokens':100,'output_tokens':1000}
    monkeypatch.setattr(writing,'call',provider)
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True))
        old=writing.validate_draft(writing.Draft.model_validate(case['persisted_proposal']),case['sources'],[],case['policy'],provisional=True)
        a=Article(**old.model_dump(mode='json'),status='draft');db.add(a);await db.flush()
        c=EditorialCandidate(fingerprint='worker-numeric',engine='evergreen',kind='comparison',topic='API guide',section='programacion',intent='Use the documented APIs',keyword='api guide',state='generating',article_id=a.id,attempts=1,details={})
        db.add(c)
        run=ResearchRun(editorial_date=NOW.date(),article_id=a.id,status='running',report={'proposal':draft.model_dump(mode='json'),'pending_review':True,'corrections_used':2})
        db.add(run);await db.commit()
        r=Redis();r.value=b'owner'
        async def collect(*args):return case['sources'],{}
        await worker.pipeline(db,run,ResearchSettings(daily_usd='.50',monthly_usd='15'),r,b'owner',collect,resume='review',policy=policy,candidate=c)
        assert a.status=='published' and calls==['Review']
        assert run.report['corrections_used']==2 and 0<run.reserved_microusd<500000
        async def check(snapshot,page):return verify_html(snapshot,'https://foroiaaldia.com',page,getter_for(snapshot))
        assert await verify_candidate(db,c,check,NOW)
        assert c.state=='published' and c.article_id==a.id
    database(operation)


def test_overlimit_search_does_not_trigger_another_paid_recovery(client):
    from test_nightly_web import seed,redis,nomination,NOW as stamp,usage
    from app.research import night_web,sources
    item=nomination();item['urls']=item['urls'][:1]
    def blocked(*args):raise sources.SourceError('Blocked','http_status',403)
    async def operation(db):
        run=await seed(db)
        report=await night_web.discover(db,run,ResearchSettings(),redis(),b'owner',stamp,
            lambda *a:(json.dumps({'candidates':[item]}),dict(usage(),_web={'search_calls':2,'complete_output':True})),
            blocked,recovery_feeds=(),official_indexes=(),alternative_provider=lambda *a:pytest.fail('No further paid search after an overrun'))
        assert report['alternative_research']['reason']=='search_tool_limit_exceeded'
        assert run.report['web_research']['accounted_microusd']>20000
    database(operation)


def test_blocked_model_nomination_can_use_a_different_official_rss_event(client):
    from test_nightly_web import seed,redis,nomination,NOW as stamp,usage
    from app.research import night_web,sources
    item=nomination();item['urls']=item['urls'][:1]
    feed=sources.Feed('https://blogs.nvidia.com/feed/','blogs.nvidia.com','nvidia')
    article='https://blogs.nvidia.com/blog/jetson-thor-release/'
    title='NVIDIA announces Jetson Thor availability'
    def fetch(url,limit):
        if url==feed.url:
            from email.utils import format_datetime
            return url,('<rss><channel><item><title>'+title+'</title><link>'+article+'</link><pubDate>'+format_datetime(stamp)+'</pubDate></item></channel></rss>').encode()
        if url==article:
            return url,('<meta property="article:published_time" content="'+stamp.isoformat()+'"><h1>'+title+'</h1><article>'+('NVIDIA announces Jetson Thor availability for developers building robotics applications. '*30)+'</article>').encode()
        raise sources.SourceError('Blocked','http_status',403)
    async def operation(db):
        run=await seed(db)
        report=await night_web.discover(db,run,ResearchSettings(),redis(),b'owner',stamp,
            lambda *a:(json.dumps({'candidates':[item]}),usage()),fetch,recovery_feeds=(feed,),official_indexes=(),
            alternative_provider=lambda *a:pytest.fail('Verified RSS event needs no extra paid search'))
        assert report['statistics']['official_feed_candidate_count']==1
        queued=[r for r in report['opportunities'] if r['reason_for_decision']=='verified_queued']
        assert len(queued)==1 and queued[0]['origin']=='official_feed'
        c=await db.scalar(select(EditorialCandidate).where(EditorialCandidate.id==queued[0]['candidate_ids'][0]))
        assert c.details['demand_source']=='official_feed'
    database(operation)


@pytest.mark.parametrize('mode',['valid','bomb','truncated','invalid'])
def test_gzip_feed_preserves_both_download_and_expanded_size_limits(monkeypatch,mode):
    import gzip
    from app.research import sources
    raw=gzip.compress(b'<rss>bounded feed</rss>' if mode!='bomb' else b'x'*10000)
    if mode=='truncated':raw=raw[:-3]
    if mode=='invalid':raw=b'not a gzip stream'
    class Response:
        status=200
        def getheader(self,key,default=None):return {'Content-Encoding':'gzip','Content-Type':'application/rss+xml'}.get(key,default)
        def read(self,limit):return raw[:limit]
    class Connection:
        def __init__(self,*a,**k):pass
        def request(self,*a,**k):pass
        def getresponse(self):return Response()
        def close(self):pass
    monkeypatch.setattr(sources,'public_addresses',lambda host:['8.8.8.8'])
    monkeypatch.setattr(sources.http.client,'HTTPSConnection',Connection)
    if mode=='valid':assert sources.fetch('https://deepmind.google/blog/rss.xml',500)[1]==b'<rss>bounded feed</rss>'
    else:
        with pytest.raises(sources.SourceError) as exc:sources.fetch('https://deepmind.google/blog/rss.xml',500)
        assert exc.value.code==('source_too_large' if mode=='bomb' else 'invalid_compression')
