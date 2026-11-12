"""Offline only: real historical source fixture, simulated model, isolated DB."""
import copy
import hashlib
import json
from datetime import timedelta

import pytest
from sqlalchemy import select, func

from test_research import client, database
from test_nightly_web import NOW, nomination, pages, seed, redis, usage
from test_rapid_news import documents, historical_draft
from test_editorial_engines import verifier, receipt
from test_evidence_first import approved_payload
from app.models import Article, EditorialCandidate
from app.research import night_web, writing, editorial, evidence
from app.research.selection import select as select_topic
from app.research.editorial_policy import policy_for, official_source, validate_scope
from app.research.config import ResearchSettings


def official():
    source = copy.deepcopy(documents()[0])
    source.update(retrieval_method='page', retrieved_at=NOW.isoformat(),
                  event_correspondence={'related':True}, announcement_scope=nomination()['event'],
                  content_sha256=hashlib.sha256(source['text'].encode()).hexdigest())
    return source


def announcement_draft(corpus):
    value = historical_draft([corpus[0],corpus[0]])
    value['title']='OpenAI presenta GPT-4o como modelo multimodal'
    value['summary']='Según OpenAI, su anuncio presenta un modelo multimodal y describe el alcance de las capacidades anunciadas.'
    return writing.resolve_grounded(writing.GroundedDraft.model_validate(value),corpus)


def test_single_official_document_is_sufficient_and_requires_real_citation():
    source=official()
    chosen, report=select_topic([source])
    assert len(chosen)==1 and report['verification_mode']=='official_announcement'
    policy=policy_for(chosen)
    corpus=evidence.catalogue(chosen)
    draft=announcement_draft(corpus)
    article=writing.validate_draft(draft,corpus,[],policy)
    assert len(article.sources)==1
    bad=draft.model_copy(deep=True)
    for p in bad.paragraphs:p.evidence=[]
    with pytest.raises(writing.StopRun,match='insufficient_independent_sources|unsupported_number'):
        writing.validate_draft(bad,corpus,[],policy)


@pytest.mark.parametrize('change',[
    {'organization_verified':False}, {'organization':'nvidia'},
    {'retrieval_method':'rss_full_content'}, {'event_correspondence':{'related':False}},
    {'content_sha256':'tampered'}, {'published':None},
    {'published':(NOW-timedelta(days=5)).isoformat()},
    {'published':(NOW+timedelta(days=1)).isoformat()},
    {'content_origin':'https://techcrunch.com/reprint'},
    {'title':'NVIDIA announces a model'},
    {'announcement_scope':'Rumors and leaked information'},
    {'announcement_scope':'An objective benchmark comparison'},
    {'announcement_scope':'An accusation by a third party'},
])
def test_official_exception_fails_closed(change):
    source=dict(official(),**change)
    assert not official_source(source)
    assert not select_topic([source])[0]


@pytest.mark.parametrize('mode',['attribution','comparison','rumor','tampered_policy'])
def test_final_scope_cannot_be_bypassed(mode):
    corpus=evidence.catalogue([official()]);policy=policy_for(corpus);draft=announcement_draft(corpus)
    if mode=='attribution':
        draft.summary='Un resultado demostrado de forma independiente.'
        draft.paragraphs[0].text='Una descripción sin identificar quién ha hecho el anuncio.'*4
    if mode=='comparison':draft.paragraphs[0].text+=' Esta comparación objetiva determina qué modelo conviene elegir.'
    if mode=='rumor':draft.paragraphs[0].text+=' Un rumor confirma el próximo lanzamiento.'
    if mode=='tampered_policy':policy['official_organization']='nvidia'
    with pytest.raises(writing.StopRun):validate_scope(draft,corpus,policy)


def test_independent_news_policy_remains_and_prompts_do_not_conflict():
    assert policy_for(documents())['min_organizations']==2
    corpus=evidence.catalogue([official()]);policy=policy_for(corpus)
    for schema, data in [(writing.Draft,{'sources':corpus}),
                         (writing.Review,{'sources':corpus,'draft':announcement_draft(corpus).model_dump()})]:
        data['editorial_policy']=dict(policy,kind='news')
        prepared=writing.prepare_request(ResearchSettings(),schema,writing.VOICE if schema is writing.Draft else writing.REVIEW_INSTRUCTIONS,data)
        prompt=prepared[2]['instructions']
        assert 'Usa al menos dos organizaciones' not in prompt
        assert 'approved=false' in prompt and 'attribution_prefix' not in prompt


def test_natural_attribution_and_company_reported_performance():
    corpus=evidence.catalogue([official()]);policy=policy_for(corpus);draft=announcement_draft(corpus)
    draft.paragraphs[0].text='OpenAI afirma que el rendimiento anunciado corresponde a sus evaluaciones internas.'
    draft.paragraphs[1].text='De acuerdo con OpenAI, estas capacidades forman parte del anuncio de la empresa.'
    validate_scope(draft,corpus,policy)
    assert official_source(dict(official(),title='OpenAI announces a model faster than its previous model'))


@pytest.mark.parametrize('approved',[True,False])
def test_full_automatic_publication_with_one_official_source_offline(client,tmp_path,monkeypatch,approved):
    calls=[]
    monkeypatch.setattr(editorial,'utcnow',lambda:NOW)
    def provider(config,payload):
        kind=payload['text']['format']['name'];calls.append(kind)
        data=json.loads(payload['input'])
        if kind=='newsresearch':value={'candidates':[dict(nomination(),urls=nomination()['urls'][:1])]};return json.dumps(value),usage()
        if kind=='groundeddraft':
            corpus=data['sources']
            value=historical_draft([corpus[0],corpus[0]])
            value.update(title='OpenAI presenta GPT-4o como modelo multimodal',summary='Según OpenAI, su anuncio presenta un modelo multimodal y describe el alcance de las capacidades anunciadas.')
        else:
            value=approved_payload(payload)
            if not approved:value.update(approved=False,supported=False,reasons=['Simulated unsupported claim: reject, never publish.'])
        return json.dumps(value),{'input_tokens':100,'output_tokens':200}
    monkeypatch.setattr(writing,'call',provider)
    async def operation(db):
        run=await seed(db)
        # Full recovery uses the historical page bytes, not a trusted flag from the model.
        from app.research import news_recovery
        async def discovery(*args,**kwargs):
            return await news_recovery.discover(*args,**kwargs,fetcher=pages,recovery_feeds=(),research_fn=night_web.research)
        monkeypatch.setattr(night_web,'discover',discovery)
        await editorial.execute(db,run,ResearchSettings(),redis(),b'owner',max_publications=1,
                                allow_evergreen=False,verifier=verifier,receipt_path=receipt(tmp_path,NOW))
        if not approved:
            assert run.status=='skipped'
            assert await db.scalar(select(func.count(Article.id)).where(Article.status=='published'))==0
            assert run.report['candidate_attempts'][-1]['reason']=='review_rejected', run.report['candidate_attempts']
            return
        assert run.status=='published', (run.reason,run.report.get('candidate_attempts'),run.report.get('generation_failure'))
        article=await db.get(Article,run.article_id)
        assert len(article.sources)==1 and article.status=='published'
        assert 'OpenAI' in article.body and 'comunicado original' in article.body
        candidate=await db.scalar(select(EditorialCandidate).where(EditorialCandidate.article_id==article.id))
        assert candidate.details['selection']['verification_mode']=='official_announcement'
        assert await db.scalar(select(func.count(Article.id)))==1
    database(operation)
    # An unchanged correction reuses the saved rejection instead of paying for
    # the identical review twice. It must still never become publishable.
    assert calls==['newsresearch','groundeddraft','groundedreview']+([] if approved else ['groundeddraft'])
