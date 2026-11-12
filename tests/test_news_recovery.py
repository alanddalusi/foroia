"""Offline regressions. Synthetic HTML is explicitly not a real historical capture."""
import json
import gzip
import base64
from pathlib import Path
import pytest
from test_nightly_web import client,database,seed,redis,nomination,pages,usage,NOW
from app.research import night_web
from app.research.config import ResearchSettings
from app.research import sources,news_gate,selection
from app.research.routes import report_view

SEC='https://www.sec.gov/Archives/edgar/data/2130357/000162828026067168/anthropicpbc-sx1.htm'

def test_recorded_five_nominations_are_retained_without_invented_documents():
    data=json.loads(Path('tests/fixtures/news_candidates_20261029.json').read_text())
    assert data['run_id']==9 and len(data['nominations'])==5
    assert 'not retained' in data['provenance']
    assert 'document_snapshots' not in data['diagnostics']
    failures=data['diagnostics']['statistics']['fetch_errors']
    sec=[e for e in failures if 'sec.gov' in e['url']]
    assert sec and all(e['http_status'] is None for e in sec)

def test_sec_is_curated_and_cannot_be_used_as_a_generic_proxy():
    assert sources.canonical(SEC)==SEC
    for url in ['https://www.sec.gov/cgi-bin/browse-edgar?action=x','https://www.sec.gov/Archives/../../secret',
                'https://www.sec.gov/Archives/edgar/data/2130357/000162828026067168/%2e%2e.htm']:
        with pytest.raises(sources.SourceError) as error:sources.canonical(url)
        assert error.value.code=='official_path_not_allowed'
    with pytest.raises(sources.SourceError):sources.canonical('https://www.sec.gov.evil.test/filing.htm')

def test_sec_host_is_not_an_independent_author():
    text='FORM S-1 Anthropic, PBC (Exact name of registrant as specified in its charter)'
    meta=sources.source_attribution(SEC,text.encode(),'unverified')
    assert meta['organization']=='anthropic' and meta['organization_verified'] is True
    assert selection.organization(dict(url=SEC,text=text,**meta))=='anthropic'
    assert sources.source_attribution(SEC,b'Unverified company filing','unverified')['organization_verified'] is False
    unknown=SEC.replace('/2130357/','/9999999/')
    assert sources.source_attribution(unknown,text.encode(),'unverified')['organization_verified'] is False

def test_sec_date_comes_from_filing_label_not_arbitrary_body_date():
    body=b'As filed with the Securities and Exchange Commission on October 26, 2026. FORM S-1'
    assert sources.publication_stamp(body,SEC)[0].isoformat()=='2026-10-26T00:00:00+00:00'
    assert sources.publication_stamp(b'Copyright October 26, 2026',SEC)[0] is None

def test_listing_query_is_preserved_but_tracking_is_removed():
    url='https://nvidianews.nvidia.com/news/latest?page=2&utm_source=search'
    assert sources.canonical(url).endswith('/news/latest?page=2')
    assert sources.is_news_index(sources.canonical(url))
    assert sources.is_news_index('https://openai.com/news/company-announcements/?display=list')
    assert sources.is_news_index('https://x.ai/company')
    assert sources.is_news_index(SEC.replace('anthropicpbc-sx1.htm','0001628280-26-067168-index.htm'))

@pytest.mark.parametrize('target,doc',[
    ('NVIDIA Vera Rubin availability on Oracle OCI','Anthropic AI for Science expands to research institutions'),
    ('Anthropic files S-1 for IPO','Anthropic AI for Science expands to research institutions'),
    ('xAI Grok Voice 3.0 release','xAI announces a partner network'),
    ('Alphabet Q3 2026 earnings','Alphabet Q2 2026 earnings'),
    ('OpenAI DevDay announcements','OpenAI Oracle apps in ChatGPT'),
])
def test_wrong_event_does_not_corroborate(target,doc):
    assert not news_gate.matches({'title':target},{'title':doc,'text':''})['related']

@pytest.mark.parametrize('target,doc',[
    ('NVIDIA Vera Rubin availability on Oracle OCI','Oracle announces NVIDIA Vera Rubin availability'),
    ('Anthropic files S-1 for IPO','Anthropic IPO filing: company submits Form S-1'),
    ('Alphabet Q3 2026 earnings','Q3 2026 earnings call: remarks from the Google CEO'),
])
def test_matching_event_can_pass_correspondence(target,doc):
    assert news_gate.matches({'title':target},{'title':doc,'text':''})['related']

def test_only_initial_filing_is_a_duplicate_not_later_developments():
    assert news_gate.initial_filing_key('Anthropic files Form S-1 for IPO')=='anthropic:initial_filing'
    assert news_gate.initial_filing_key('Anthropic amends Form S-1 for IPO') is None
    assert news_gate.initial_filing_key('Anthropic IPO pricing update') is None

def test_private_snapshot_and_raw_provider_response_are_not_sent_to_panel():
    data=report_view({'editorial_version':2,'news_discovery':{'document_snapshots':[{'text':'private snapshot'}],
        'web':{'raw':'provider raw','usage':{'input_tokens':1},'verified_candidates':1},'opportunities':[]}})
    assert 'private snapshot' not in json.dumps(data) and 'provider raw' not in json.dumps(data)
    assert data['web_discovery']['web']['verified_candidates']==1

def test_index_is_resolved_to_individual_article_before_queueing(client):
    item=nomination();original=item['urls'][0];index='https://openai.com/news/company-announcements/'
    item['urls'][0]=index
    calls=[]
    def fetch(url,limit):
        calls.append(url)
        if url==index:return url,('<h1>Company announcements</h1><a href="'+original+'">'+item['title']+'</a>').encode()
        return pages(url,limit)
    async def operation(db):
        run=await seed(db)
        report=await night_web.discover(db,run,ResearchSettings(),redis(),b'owner',NOW,
            lambda *a:(json.dumps({'candidates':[item]}),usage()),fetch,recovery_feeds=())
        assert report['opportunities'][0]['reason_for_decision']=='verified_queued'
        assert report['index_expansion'][0]['article_urls']==[original]
        assert index not in {d['url'] for d in report['document_snapshots']}
        assert len(report['document_snapshots'])==2
    database(operation)
    assert calls.count(index)==1

def test_cached_403_is_visible_for_each_candidate_and_not_refetched(client):
    item=nomination();item['urls']=item['urls'][:1];calls=[]
    def blocked(url,limit):
        calls.append(url);raise sources.SourceError('Forbidden','http_status',403)
    async def operation(db):
        run=await seed(db)
        report=await night_web.discover(db,run,ResearchSettings(),redis(),b'owner',NOW,
            lambda *a:(json.dumps({'candidates':[item,dict(item,title=item['title']+' update')]}),usage()),blocked,recovery_feeds=())
        assert report['web']['verified_candidates']==0
        for row in report['opportunities']:
            assert row['reason_for_decision']=='document_inaccessible'
            assert row['diagnostics'][0]['http_status']==403
        assert report['statistics']['generation_calls_avoided']==2
    database(operation)
    assert len(calls)==1

def test_five_recorded_proposals_with_fresh_vps_capture_are_replayed_offline(client):
    """Actual saved HTTP bytes, fresh timestamp, no model or live HTTP calls."""
    from datetime import datetime
    from app.models import Article
    from test_articles_api import article
    data=json.loads(Path('tests/fixtures/news_candidates_20261029.json').read_text())
    capture=json.loads(gzip.decompress(Path('tests/fixtures/news_http_capture_20261029.json.gz').read_bytes()))
    now=datetime.fromisoformat(capture['rows'][0]['captured_at'])
    saved={sources.canonical(r['requested_url']):r for r in capture['rows']}
    def fetch(url,limit):
        row=saved.get(url)
        if row is None:raise sources.SourceError('Not present in recorded capture','offline_not_captured')
        if row.get('error'):raise sources.SourceError('Recorded transport error',row['error'],row.get('http_status'))
        return row['final_url'],base64.b64decode(row['body_base64'])
    async def research(*args):return [night_web.NewsOpportunity.model_validate(n) for n in data['nominations']],{}
    async def operation(db):
        from app.research.news_recovery import discover
        run=await seed(db)
        db.add(Article(**{**article(),'title':'Anthropic presenta la documentación S-1 para su salida a bolsa',
            'slug':'existing-anthropic-filing','sources':[]},status='published',published_at=now))
        await db.commit()
        report=await discover(db,run,ResearchSettings(),redis(),b'owner',now,
            fetcher=fetch,recovery_feeds=(),research_fn=research)
        decisions=report['opportunities']
        # Priority sorting preserves original relative order for major releases.
        by_title={r['title']:r for r in decisions}
        actual=[by_title[n['title']] for n in data['nominations']]
        assert actual[0]['reason_for_decision']=='already_published'
        assert any(d['http_status']==403 for d in actual[1]['diagnostics'])
        assert actual[2]['verified_source_urls']==[capture['rows'][-2]['final_url']],json.dumps(actual[2]['diagnostics'])
        assert actual[2]['reason_for_decision']=='verified_queued'
        assert actual[2]['verification']['verification_mode']=='official_announcement'
        assert not actual[3]['verified_source_urls']
        assert any(d['reason']=='document_stale' for d in actual[3]['diagnostics'])
        assert actual[4]['reason_for_decision']=='independent_corroboration_missing'
        assert len(actual[4]['verified_source_urls'])==1
        assert report['statistics']['generation_calls_avoided']==4
    database(operation)
