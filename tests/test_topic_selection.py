"""Offline topic/provenance gate; real regressions contain no private drafts or PII."""
import asyncio
import copy
import json
from datetime import UTC, datetime
from html import escape
from itertools import combinations

import pytest

from test_research import EVIDENCE, Redis, client, database, draft, review
from test_evidence_first import grounded, approved_payload
from app.models import ResearchControl, ResearchRun, Article
from app.research import evidence, selection, sources, worker, writing
from app.research.config import ResearchSettings


def pair():
    return copy.deepcopy(EVIDENCE)


def test_valid_bilingual_concept_selects_balanced_independent_sources():
    docs = pair()
    docs[0]['title'] = 'Inferencia local: cómo ejecutar modelos en tu equipo'
    docs[1]['title'] = 'On-device inference for downloadable open models'
    docs.append(dict(docs[0], id=3, url='https://openai.com/news/second', text='A distinct technical deployment discussion. ' * 30))
    chosen, report = selection.select(docs)
    assert len(chosen)==2 and {s['organization'] for s in chosen} == {'openai','huggingface'}
    assert report['selected_topic_id'] and report['generation_calls_avoided']==0
    assert all(selection.relationship(a,b)['related'] for a,b in combinations(chosen,2))
    assert selection.select(list(reversed(docs)))[1]['selected_topic_id'] == report['selected_topic_id']


@pytest.mark.parametrize('mode', ['same_organization','identical','reproduced','same_origin','wrong_identity','unknown_byline','unrelated'])
def test_rejects_nonindependence_and_unrelated_material_before_generation(mode):
    docs = pair()
    if mode == 'same_organization':
        docs[1].update(url='https://www.microsoft.com/en-us/research/example',organization='microsoft')
        docs[0].update(url='https://huggingface.co/blog/microsoft/example',organization='microsoft')
    if mode == 'identical': docs[1]['text'] = docs[0]['text']
    if mode == 'reproduced': docs[1]['text'] = 'Republished announcement. ' + docs[0]['text'] + ' More publisher navigation.'
    if mode == 'same_origin': docs[1]['content_origin'] = docs[0]['url']
    if mode == 'wrong_identity': docs[1].update(url='https://blog.google/ai/example',organization='microsoft')
    if mode == 'unknown_byline': docs[1].update(url='https://huggingface.co/blog/unknown/example',organization='ai2')
    if mode == 'unrelated': docs[1].update(title='Automated greenhouse irrigation',text='Sensors regulate moisture and ventilation in a greenhouse. ' * 30)
    chosen, report = selection.select(docs)
    assert chosen==[] and report['generation_calls_avoided']==1
    assert not report['selected_topic_id']
    assert report['excluded_documents'] or all(c['status']=='rejected' for c in report['candidates'])


def test_real_microsoft_regression_has_one_author_despite_two_hosts():
    docs = [dict(EVIDENCE[0],organization='microsoft',url='https://huggingface.co/blog/microsoft/thinkingbox-training',
                 title='Turning Database Grading into RL Rewards: Post-Training Agents with ThinkingBox',
                 text='ThinkingBox turns executable checks of terminal database state into rewards for post-training agents. ' * 12),
            dict(EVIDENCE[1],organization='microsoft',url='https://www.microsoft.com/en-us/research/blog/flint-interactive/',
                 title='Flint-interactive: A language for creating interactive data visualizations',
                 text='Interactive data visualizations support analysis and chart exploration. ' * 18)]
    chosen, report = selection.select(docs)
    assert chosen==[]
    assert all(c['organizations']==['microsoft'] for c in report['candidates'])
    assert all(len(c['source_ids'])==1 for c in report['candidates'])


def test_cross_host_redirect_identity_and_reprint_canonical():
    result = sources.source_attribution('https://blog.google/ai/example',b'','openai')
    assert result['organization']=='google' and result['organization_verified']
    html=b'<link rel="canonical" href="https://openai.com/news/original">'
    assert sources.content_origin('https://blog.google/ai/copy',html)=='https://openai.com/news/original'


def test_final_article_must_cite_both_selected_organizations():
    chosen,_=selection.select(pair())
    proposal=draft()
    for paragraph in proposal.paragraphs:
        for ref in paragraph.evidence: ref.source_id=1
    with pytest.raises(writing.StopRun,match='insufficient_independent_sources'):
        writing.validate_draft(proposal,chosen,[])


def test_rss_title_can_nominate_fetch_but_cannot_pass_final_selection():
    docs=pair();docs[0]['title']='LitPivot proposal faceting'
    metadata=dict(docs[1],title='LitPivot proposal editor');metadata.pop('text')
    assert selection.relationship(docs[0],metadata)['related']
    chosen,report=selection.select([docs[0],metadata])
    assert not chosen and any(s['reason']=='insufficient_document_content' for s in report['excluded_documents'])


def test_rejected_candidate_does_not_prevent_next_valid_topic():
    docs = pair()
    unrelated = dict(docs[0],id=99,url='https://openai.com/news/irrigation',title='Greenhouse irrigation sensors',text='Watering systems improve crop moisture. ' * 30)
    chosen, report = selection.select([unrelated,*docs])
    assert {s['id'] for s in chosen}=={1,2}
    assert report['rejected_candidates']>=1
    assert report['generation_calls_avoided']==0


def test_related_recovery_uses_unused_authorized_entry_once_and_respects_bounds(monkeypatch):
    docs = pair(); calls=[]
    encoded=escape(json.dumps({'authors':[{'author':{'isHf':True}}]}),quote=True)
    html=('<div data-target="BlogAuthorsByline" data-props="'+encoded+'"></div><p>'+docs[1]['text']+'</p>').encode()
    def fetch(url): calls.append(url); return url,html
    monkeypatch.setattr(sources,'fetch',fetch)
    pending={k:v for k,v in docs[1].items() if k!='text'}
    stats={'fetch_attempts':1,'attempted_urls':[docs[0]['url']],'unfetched_candidates':[pending]}
    result, report=asyncio.run(sources.recover_related(docs[:1],stats))
    assert len(result)==2 and calls==[docs[1]['url']] and selection.select(result)[0]
    assert report['fetch_attempts']==2
    calls.clear()
    asyncio.run(sources.recover_related(docs[:1],dict(stats,fetch_attempts=12)))
    assert calls==[]


def test_failed_related_recovery_does_not_retry_403(monkeypatch):
    docs=pair();calls=[]
    def fetch(url): calls.append(url);raise sources.SourceError('blocked','http_status',403)
    monkeypatch.setattr(sources,'fetch',fetch)
    stats={'fetch_attempts':1,'attempted_urls':[docs[0]['url']],'unfetched_candidates':[docs[1],docs[1]]}
    result,report=asyncio.run(sources.recover_related(docs[:1],stats))
    assert calls==[docs[1]['url']] and result==docs[:1]
    assert report['fetch_errors'][0]['http_status']==403


def test_initial_collection_reserves_real_capacity_for_complementary_fetch(monkeypatch):
    now=datetime(2026,10,24,12,tzinfo=UTC);calls=[]
    xml=('<rss><channel>'+''.join(
        f'<item><title>Local inference document {i}</title><link>https://openai.com/news/entry-{i}</link>'
        '<pubDate>Sat, 24 Oct 2026 10:00:00 GMT</pubDate></item>' for i in range(9))+'</channel></rss>').encode()
    def fetch(url,max_bytes=sources.MAX_BYTES):
        if url in {f.url for f in sources.FEEDS}:
            return url,xml if url==sources.FEEDS[0].url else b'<rss/>'
        calls.append(url)
        return url,('<p>Local inference technical context for '+url+' '+('Verified deployment details. '*35)+'</p>').encode()
    monkeypatch.setattr(sources,'fetch',fetch)
    docs,stats=asyncio.run(sources.collect(now,set(),initial_document_limit=6))
    assert len(docs)==6 and len(calls)==6 and len(stats['unfetched_candidates'])==3
    recovered,stats=asyncio.run(sources.recover_related(docs,stats))
    assert len(recovered)==8 and len(calls)==8 and stats['fetch_attempts']==8
    assert len(set(calls))==8 and stats['related_recovery']['attempts']


@pytest.mark.parametrize('valid',[False,True])
def test_complete_topic_gate_and_publication_without_paid_calls(client,monkeypatch,valid):
    docs=pair(); calls=[]
    unrelated=dict(docs[0],id=99,url='https://openai.com/news/watering',title='Greenhouse watering control',text='Humidity control for growing vegetables. '*30)
    if not valid: docs[1]['text']=docs[0]['text']
    def provider(config,payload):
        calls.append(payload['text']['format']['name'])
        data=json.loads(payload['input'])
        assert {s['id'] for s in data['sources']}=={1,2}
        if calls[-1]=='groundeddraft':value=grounded(evidence.catalogue(pair())).model_dump()
        else:value=approved_payload(payload)
        return json.dumps(value),{'input_tokens':10,'output_tokens':100}
    monkeypatch.setattr(writing,'call',provider)
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True));row=ResearchRun(editorial_date=datetime(2026,10,24).date())
        db.add(row);await db.commit();redis=Redis();redis.value=b'owner'
        async def collect(now,urls):return [unrelated,*docs],{}
        if valid:await worker.pipeline(db,row,ResearchSettings(),redis,b'owner',collect,writing.generate)
        else:
            with pytest.raises(writing.StopRun,match='insufficient_independent_topic_sources'):
                await worker.pipeline(db,row,ResearchSettings(),redis,b'owner',collect,writing.generate)
        assert row.report['selection']['generation_calls_avoided']==(0 if valid else 1)
        if valid:
            assert row.status=='published' and len(calls)==2 and row.reserved_microusd<=150000
            article=await db.get(Article,row.article_id); assert len(article.sources)==2
        else:assert row.article_id is None and row.reserved_microusd==0 and calls==[]
    database(operation)
    assert len(client.get('/articles').json()['items'])==(1 if valid else 0)
