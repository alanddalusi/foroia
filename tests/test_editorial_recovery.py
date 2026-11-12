import asyncio
import copy
from datetime import timedelta
import json

import pytest
from sqlalchemy import select,func

from test_research import EVIDENCE,Redis,client,database
from test_editorial_engines import NOW,receipt,docs,no_news,verifier,provider_factory
from test_articles_api import article as article_payload
from app.models import Article,EditorialCandidate,GenerationUsage,ResearchRun,ResearchControl,SourceCache
from app.research import editorial,queue,writing,evidence
from app.research.config import ResearchSettings
from app.research.publication import article_snapshot,verify_candidate,PublicationError


@pytest.mark.parametrize('mode',['daily','monthly'])
def test_budget_caps_stop_before_provider(client,tmp_path,monkeypatch,mode):
    monkeypatch.setattr(editorial,'utcnow',lambda:NOW)
    def forbidden(*args):pytest.fail('No provider call may be made after a cap')
    monkeypatch.setattr(writing,'call',forbidden)
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True))
        if mode=='monthly':db.add(ResearchRun(editorial_date=NOW.date()-timedelta(days=1),status='skipped',reserved_microusd=4_999_999))
        run=ResearchRun(editorial_date=NOW.date());db.add(run);await db.commit();redis=Redis();redis.value=b'owner'
        await editorial.execute(db,run,ResearchSettings(daily_usd='0' if mode=='daily' else '.15'),redis,b'owner',
            news_collector=no_news,doc_loader=docs,verifier=verifier,receipt_path=receipt(tmp_path))
        assert run.reserved_microusd==0 and run.reason=='budget_exhausted'
        assert await db.scalar(select(func.count()).select_from(GenerationUsage))==0
    database(operation)


def test_restart_recovers_preflight_but_never_unknown_generation(client):
    async def operation(db):
        await queue.seed_evergreen(db)
        rows=(await db.scalars(select(EditorialCandidate).limit(2))).all()
        for row,state in zip(rows,['preparing','generating']):row.state=state;row.updated_at=NOW-timedelta(hours=1)
        await db.commit();await editorial.recover_queue(db,NOW)
        assert rows[0].state=='queued' and rows[0].reason=='preflight_interrupted'
        assert rows[1].state=='technical_error' and rows[1].reason=='interrupted_uncertain_generation'
    database(operation)


def test_pending_review_resumes_next_day_without_redrafting(client,tmp_path,monkeypatch):
    monkeypatch.setattr(editorial,'utcnow',lambda:NOW)
    calls=[];base=provider_factory(calls)
    def first(config,payload):
        if payload['text']['format']['name']=='groundedreview':raise writing.StopRun('incomplete_generation')
        return base(config,payload)
    monkeypatch.setattr(writing,'call',first)
    path=receipt(tmp_path)
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True));one=ResearchRun(editorial_date=NOW.date());db.add(one);await db.commit()
        redis=Redis();redis.value=b'owner'
        await editorial.execute(db,one,ResearchSettings(),redis,b'owner',news_collector=no_news,doc_loader=docs,verifier=verifier,receipt_path=path)
        aid=one.article_id;assert aid and one.status=='draft'
        candidate=await db.scalar(select(EditorialCandidate).where(EditorialCandidate.article_id==aid))
        assert candidate.state=='deferred' and candidate.details['resume_report']['pending_review']
        next_day=NOW+timedelta(days=1)
        monkeypatch.setattr(editorial,'utcnow',lambda:next_day)
        monkeypatch.setattr(writing,'call',base)
        two=ResearchRun(editorial_date=next_day.date());db.add(two);await db.commit()
        await editorial.execute(db,two,ResearchSettings(),redis,b'owner',news_collector=no_news,doc_loader=docs,verifier=verifier,receipt_path=path)
        assert two.status=='published' and two.article_id==aid
        assert [kind for kind,_ in calls].count('evergreendraft')==1
        assert await db.scalar(select(func.count()).select_from(Article))==1
    database(operation)


def test_human_edit_blocks_automatic_withdrawal(client):
    async def operation(db):
        article=Article(**article_payload(),status='published',published_at=NOW);db.add(article);await db.flush()
        candidate=EditorialCandidate(fingerprint='f'*64,engine='evergreen',kind='guide',topic='Topic',section='tutoriales',intent='Intent',keyword='Keyword',state='needs_verification',article_id=article.id,details={'publication_snapshot':article_snapshot(article)})
        db.add(candidate);await db.commit()
        article.body='Edición legítima posterior que debe conservarse.';await db.commit()
        assert not await verify_candidate(db,candidate,verifier,NOW)
        assert article.status=='published' and article.body.startswith('Edición legítima') and candidate.reason=='article_changed'
    database(operation)


def test_update_preserves_slug_publication_date_and_restores_on_critical_failure(client,tmp_path,monkeypatch):
    monkeypatch.setattr(editorial,'utcnow',lambda:NOW)
    calls=[];monkeypatch.setattr(writing,'call',provider_factory(calls))
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True))
        article=Article(**article_payload(),status='published',published_at=NOW-timedelta(days=40));db.add(article);await db.flush()
        snapshot=article_snapshot(article)
        candidate=EditorialCandidate(fingerprint='d'*64,engine='evergreen',kind='update',topic='Actualización del ejemplo JSON',section='programacion',intent='Revisar documentación',keyword='validar json python',priority=99,state='queued',target_article_id=article.id,
            details={'blueprint':'json-validation','target_snapshot':snapshot,'previous_evidence_quotes':['Previous documented behavior which has now been replaced.']})
        db.add(candidate);run=ResearchRun(editorial_date=NOW.date());db.add(run);await db.commit()
        redis=Redis();redis.value=b'owner'
        await editorial.execute(db,run,ResearchSettings(),redis,b'owner',news_collector=no_news,doc_loader=docs,verifier=verifier,receipt_path=receipt(tmp_path))
        await db.refresh(article)
        assert article.slug==snapshot['slug'] and article_snapshot(article)['published_at']==snapshot['published_at']
        assert article.body!=snapshot['body'] and candidate.state=='published'
        candidate.state='needs_verification';await db.commit()
        async def failure(snapshot,page):raise PublicationError('publication_schema_mismatch')
        assert not await verify_candidate(db,candidate,failure,NOW)
        await db.refresh(article)
        assert article_snapshot(article)==snapshot and article.status=='published'
    database(operation)


def test_unknown_example_or_raw_code_cannot_be_published(client,tmp_path,monkeypatch):
    from test_editorial_engines import tutorial_payload
    async def operation(db):
        await queue.seed_evergreen(db)
        candidate=await db.scalar(select(EditorialCandidate).where(EditorialCandidate.keyword=='validar json ia python'))
        sources,policy=await queue.prepare_candidate(db,candidate,NOW,{'remaining':4},doc_loader=docs,receipt_path=receipt(tmp_path))
        async def reserve(cost):pass
        def bad(config,payload):
            value=tutorial_payload(payload);value['example_ids']=['arbitrary_code']
            return json.dumps(value),{'input_tokens':1,'output_tokens':1}
        monkeypatch.setattr(writing,'call',bad)
        with pytest.raises(writing.StopRun,match='invalid_example'):
            await writing.generate(ResearchSettings(),writing.Draft,writing.VOICE,{'sources':evidence.catalogue(sources),'editorial_policy':policy},reserve)
    database(operation)
