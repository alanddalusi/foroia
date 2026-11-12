"""No paid calls: editorial rejection, bounded rewrite and factual safeguards."""
import copy,json,re
from pathlib import Path
from decimal import Decimal

import pytest
from sqlalchemy import select,func
from test_research import client,database,Redis,review
from test_articles_api import AUTH
from test_editorial_engines import NOW,no_news,docs,verifier,receipt,provider_factory
from test_evidence_first import approved_payload
from test_editorial_matrix import plan_provider
from app.models import ResearchControl,ResearchRun,Article
from app.research import editorial,writing,evidence
from app.research.config import ResearchSettings
from app.research.style import issues,validate,STYLE_FLAGS
from app.research.editorial_policy import policy_for
from test_official_announcements import official,announcement_draft

SAVED=json.loads(Path('tests/fixtures/official_vscode_20261029.json').read_text(encoding='utf-8'))


def test_real_published_repetition_is_rejected_without_losing_evidence():
    draft=writing.Draft.model_validate(SAVED['draft'])
    errors={e['code'] for e in issues(draft)}
    assert {'attribution_headings','repeated_attribution','oversegmented'} <= errors
    assert all(p.evidence for p in draft.paragraphs)
    with pytest.raises(writing.StopRun,match='editorial_style_rejected'):validate(draft)


def test_natural_three_sections_keep_attribution_and_citations():
    sources=evidence.catalogue([official()]);draft=announcement_draft(sources)
    draft.paragraphs[2].text+=' '+draft.paragraphs[3].text
    draft.paragraphs=draft.paragraphs[:3]
    validate(draft)
    policy=policy_for(sources)
    value=writing.validate_draft(draft,sources,[],policy)
    assert value.body.count('## ')==3
    assert value.sources and 'comunicado original' in value.body
    assert value.body.count('https://')==1


def test_review_contract_requires_each_editorial_verdict_and_drops_old_prefix_rule():
    sources=evidence.catalogue([official()]);draft=announcement_draft(sources)
    policy=dict(policy_for(sources),attribution_prefix='According to stale policy',scope='attribute every paragraph')
    prepared=writing.prepare_request(ResearchSettings(),writing.Review,writing.REVIEW_INSTRUCTIONS,{'draft':draft.model_dump(),'sources':sources,'editorial_policy':policy})
    request=prepared[2];shape=request['text']['format']['schema']
    assert set(STYLE_FLAGS)<=set(shape['required'])
    assert all('default' not in shape['properties'][k] for k in STYLE_FLAGS)
    data=json.loads(request['input'])
    assert 'attribution_prefix' not in data['editorial_policy']
    assert 'attribute every paragraph' not in request['input']
    assert 'attribution_prefix' not in request['instructions']
    assert 'non_repetitive' in request['instructions']


@pytest.mark.parametrize('mode',['mechanical','semantic','uncorrected'])
def test_automatic_style_rewrite_is_bounded_and_required_before_publication(client,tmp_path,monkeypatch,mode):
    monkeypatch.setattr(editorial,'utcnow',lambda:NOW)
    calls=[];review_count=0;draft_count=0
    base=provider_factory([])
    def provider(config,payload):
        nonlocal review_count,draft_count
        kind=payload['text']['format']['name'];calls.append(kind)
        if kind=='evergreendraft':
            draft_count+=1
            raw,usage=base(config,payload);value=json.loads(raw)
            if mode=='semantic' and draft_count>1:
                value['paragraphs'][0]['text']+=' Esa separación evita confundir un documento bien formado con un hecho contrastado.'
            if mode in {'mechanical','uncorrected'} and (draft_count==1 or mode=='uncorrected'):
                for p in value['paragraphs']:p['heading']='Según OpenAI, '+p['heading'];p['text']='Según OpenAI, '+p['text']
            return json.dumps(value),usage
        review_count+=1;value=approved_payload(payload)
        if mode=='semantic' and review_count==1:
            value.update(approved=False,natural=False,non_repetitive=False,reasons=['Reescribir el desarrollo: suena traducido y repite ideas.'])
        return json.dumps(value),{'input_tokens':100,'output_tokens':200}
    monkeypatch.setattr(writing,'call',provider)
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True));run=ResearchRun(editorial_date=NOW.date());db.add(run);await db.commit()
        redis=Redis();redis.value=b'owner'
        await editorial.execute(db,run,ResearchSettings(),redis,b'owner',news_collector=no_news,doc_loader=docs,verifier=verifier,receipt_path=receipt(tmp_path))
        articles=(await db.scalars(select(Article).where(Article.status=='published'))).all()
        if mode=='uncorrected':
            assert not articles
            assert 'groundedreview' not in calls
        else:
            assert run.status=='published' and len(articles)==1
            assert all(run.report['editorial_style']['checks'].values())
            assert run.report['corrections_used']==1 and draft_count==2
        assert run.reserved_microusd<=150000
    database(operation)


def test_prepared_microsoft_revision_has_three_sections_and_original_source():
    value=json.loads(Path('editorial/revisions/microsoft-copilot-harness-natural.json').read_text(encoding='utf-8'))
    body=value['body']
    assert body.count('## ')==3 and 'Según Microsoft' not in body
    assert SAVED['source']['url'] in body and '[1]' in body
    assert 'Microsoft sostiene' in body and 'mediciones independientes' in body
    assert all(key not in value for key in ('slug','published_at','title','sources'))


def test_edit_published_story_preserves_original_date_url_and_sources(client):
    source=SAVED['source']
    original={'slug':'microsoft-copilot-style-regression','title':SAVED['draft']['title'],
              'summary':SAVED['draft']['summary'],'body':'\n\n'.join('## '+p['heading']+'\n'+p['text']+' [1]' for p in SAVED['draft']['paragraphs']),
              'section':'actualidad','author_name':'Redacción Foro IA al Día',
              'sources':[{'url':source['url'],'title':source['title'],'language':'en'}]}
    r=client.post('/editorial/articles',headers=AUTH,json=original);assert r.status_code==201
    identifier=r.json()['id']
    for status in ['review','published']:
        r=client.post(f'/editorial/articles/{identifier}/status',headers=AUTH,json={'status':status});assert r.status_code==200
    before=r.json()
    revision=json.loads(Path('editorial/revisions/microsoft-copilot-harness-natural.json').read_text(encoding='utf-8'))
    r=client.patch(f'/editorial/articles/{identifier}',headers=AUTH,json=revision);assert r.status_code==200
    after=r.json()
    assert all(after[key]==before[key] for key in ['id','slug','published_at','status','sources','title'])
    public=client.get('/articles/'+after['slug']);assert public.status_code==200
    assert public.json()['body']==revision['body'] and public.json()['body'].count('## ')==3
