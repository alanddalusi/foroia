"""Two real coordinator workspaces; simulated models, isolated DB, no paid calls."""
import copy
import json
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, func

from test_research import client, database, EVIDENCE, Redis
from test_editorial_engines import NOW, receipt, docs, no_news, provider_factory, verifier
from app.models import ResearchControl, ResearchRun, EditorialLaneRun, Article, GenerationUsage
from app.research import editorial, lanes, writing
from app.research.config import ResearchSettings
from app.research.publication import PublicationError


@pytest.mark.parametrize('mode', ['both', 'no_news', 'research_error', 'news_error', 'practical_error', 'news_verification_pending'])
def test_independent_lanes_reuse_existing_pipeline_and_budget(client, tmp_path, monkeypatch, mode):
    monkeypatch.setattr(editorial, 'utcnow', lambda: NOW)
    monkeypatch.setattr(lanes, 'utcnow', lambda: NOW)
    calls = []
    news = [dict(s, published=NOW.isoformat()) for s in copy.deepcopy(EVIDENCE)]
    base = provider_factory(calls, news=news)
    def provider(config, payload):
        engine = json.loads(payload['input']).get('editorial_policy', {}).get('kind')
        if (mode == 'news_error' and engine == 'news') or (mode == 'practical_error' and engine != 'news'):
            raise writing.StopRun('provider_unavailable')
        return base(config, payload)
    monkeypatch.setattr(writing, 'call', provider)
    async def collect(now, urls):
        if mode == 'research_error': raise writing.StopRun('provider_unavailable')
        return ([] if mode == 'no_news' else news), {'candidate_count': 2}
    async def verify(snapshot, page):
        if mode == 'news_verification_pending' and snapshot['section'] == 'actualidad':
            raise PublicationError('publication_temporarily_unavailable', True)
        return await verifier(snapshot, page)
    async def operation(db):
        db.add(ResearchControl(id=1, enabled=True))
        run = ResearchRun(editorial_date=NOW.date(), report={})
        db.add(run); await db.commit()
        redis = Redis(); redis.value = b'owner'
        config = ResearchSettings(daily_usd=Decimal('.20'), monthly_usd=Decimal('10'), two_lanes=True)
        options = dict(news_collector=collect, doc_loader=docs, verifier=verify, receipt_path=receipt(tmp_path))
        await lanes.execute(db, run, config, redis, b'owner', **options)
        rows = (await db.scalars(select(EditorialLaneRun).order_by(EditorialLaneRun.id))).all()
        assert len(rows) == 2
        by = {r.engine:r for r in rows}
        assert by['evergreen'].status == ('skipped' if mode == 'practical_error' else 'published'), [(r.engine,r.reason) for r in rows]
        assert by['news'].status == ('published' if mode in {'both','practical_error'} else 'needs_verification' if mode == 'news_verification_pending' else 'skipped')
        assert 0 < run.reserved_microusd <= 200000
        assert await db.scalar(select(func.sum(GenerationUsage.estimated_microusd))) <= run.reserved_microusd
        assert len(run.report['publications']) == (2 if mode == 'both' else 1)
        before_calls = len(calls)
        # Re-entering a finished day cannot spend again or publish another article.
        if mode != 'news_verification_pending':
            await lanes.execute(db, run, config, redis, b'owner', **options)
            assert len(calls) == before_calls
            assert len(run.report['publications']) == (2 if mode == 'both' else 1)
        assert await db.scalar(select(func.count(Article.id)).where(Article.status == 'published')) == (2 if mode in {'both','news_verification_pending'} else 1)
        assert run.report['planned_publications'] == 2
    database(operation)


def test_flag_is_off_and_existing_budget_and_schedule_remain_unchanged(monkeypatch):
    from app.research.config import settings
    monkeypatch.delenv('RESEARCH_TWO_LANES', raising=False)
    assert not settings().two_lanes
    config = ResearchSettings(daily_usd='.20',monthly_usd='10')
    assert str(config.at)=='22:30:00'
    assert settings().practical_publications==1  # Never activates the proposal implicitly.
    with pytest.raises(ValueError): ResearchSettings(daily_usd='.51',monthly_usd='15')


@pytest.mark.parametrize('crash_event',['response','calling'])
def test_restart_replays_received_draft_without_another_generation(client,tmp_path,monkeypatch,crash_event):
    from app.research import checkpoints
    class Crash(BaseException): pass
    monkeypatch.setattr(editorial,'utcnow',lambda:NOW)
    monkeypatch.setattr(lanes,'utcnow',lambda:NOW)
    calls=[];monkeypatch.setattr(writing,'call',provider_factory(calls))
    real=checkpoints.store_for;crashed=False
    def store_for(db,run):
        original=real(db,run)
        async def store(event,key,data):
            nonlocal crashed
            result=await original(event,key,data)
            if event==crash_event and not crashed:
                crashed=True
                raise Crash()
            return result
        return store
    monkeypatch.setattr(checkpoints,'store_for',store_for)
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True));run=ResearchRun(editorial_date=NOW.date(),report={})
        db.add(run);await db.commit();rid=run.id
        redis=Redis();redis.value=b'owner'
        config=ResearchSettings(daily_usd='.20',monthly_usd='10',two_lanes=True)
        options=dict(news_collector=no_news,doc_loader=docs,verifier=verifier,receipt_path=receipt(tmp_path))
        with pytest.raises(Crash):await lanes.execute(db,run,config,redis,b'owner',**options)
        await db.close()
        run=await db.get(ResearchRun,rid);redis.value=b'restarted'
        await lanes.execute(db,run,config,redis,b'restarted',**options)
        assert run.status==('published' if crash_event=='response' else 'skipped'),run.report
        assert [kind for kind,engine in calls]==(['evergreendraft','groundedreview'] if crash_event=='response' else [])
        assert await db.scalar(select(func.count(Article.id)))==(1 if crash_event=='response' else 0)
        assert 0<run.reserved_microusd<200000
    database(operation)


def test_pending_lane_review_resumes_next_day_without_redrafting(client,tmp_path,monkeypatch):
    monkeypatch.setattr(editorial,'utcnow',lambda:NOW)
    monkeypatch.setattr(lanes,'utcnow',lambda:NOW)
    calls=[];base=provider_factory(calls);failed=False
    def provider(config,payload):
        nonlocal failed
        if payload['text']['format']['name']=='groundedreview' and not failed:
            failed=True
            raise writing.StopRun('incomplete_generation')
        return base(config,payload)
    monkeypatch.setattr(writing,'call',provider)
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True));one=ResearchRun(editorial_date=NOW.date(),report={})
        db.add(one);await db.commit()
        redis=Redis();redis.value=b'owner'
        config=ResearchSettings(daily_usd='.20',monthly_usd='10',two_lanes=True)
        options=dict(news_collector=no_news,doc_loader=docs,verifier=verifier,receipt_path=receipt(tmp_path))
        await lanes.execute(db,one,config,redis,b'owner',**options)
        first=await db.scalar(select(EditorialLaneRun).where(EditorialLaneRun.engine=='evergreen'))
        aid=first.article_id;assert aid and first.status=='draft'
        tomorrow=NOW+timedelta(days=1)
        monkeypatch.setattr(editorial,'utcnow',lambda:tomorrow)
        monkeypatch.setattr(lanes,'utcnow',lambda:tomorrow)
        two=ResearchRun(editorial_date=tomorrow.date(),report={});db.add(two);await db.commit()
        await lanes.execute(db,two,config,redis,b'owner',**options)
        assert two.status=='published' and two.article_id==aid,two.report
        assert [kind for kind,engine in calls].count('evergreendraft')==1
        assert await db.scalar(select(func.count(Article.id)))==1
    database(operation)


def test_existing_scheduler_runs_both_lanes_once_at_2230_madrid(client,tmp_path,monkeypatch):
    from contextlib import asynccontextmanager
    from app.research import worker
    stamp=NOW.replace(day=25,hour=21,minute=29,second=59)
    redis=Redis();calls=[]
    config=ResearchSettings(api_key='offline-test',daily_usd='.20',monthly_usd='10',two_lanes=True)
    monkeypatch.setattr(worker,'utcnow',lambda:stamp)
    monkeypatch.setattr(editorial,'utcnow',lambda:stamp)
    monkeypatch.setattr(lanes,'utcnow',lambda:stamp)
    monkeypatch.setattr(worker,'get_redis',lambda:redis)
    monkeypatch.setattr(worker,'settings',lambda:config)
    news=[dict(s,published=stamp.isoformat()) for s in copy.deepcopy(EVIDENCE)]
    monkeypatch.setattr(writing,'call',provider_factory(calls,news=news))
    async def collect(now,urls):return news,{'candidate_count':2}
    execute=lanes.execute
    async def coordinated(db,run,config,redis,token,**kwargs):
        await execute(db,run,config,redis,token,news_collector=collect,doc_loader=docs,
            verifier=verifier,receipt_path=receipt(tmp_path,stamp))
    monkeypatch.setattr(lanes,'execute',coordinated)
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True));await db.commit()
        @asynccontextmanager
        async def session():yield db
        monkeypatch.setattr(worker,'get_sessionmaker',lambda:session)
        await worker.tick();assert calls==[]
        nonlocal stamp
        stamp+=timedelta(seconds=1)
        await worker.tick()
        assert len(calls)==4
        await db.close()
        await worker.tick();assert len(calls)==4
        assert await db.scalar(select(func.count(Article.id)).where(Article.status=='published'))==2
        assert await db.scalar(select(func.count(ResearchRun.id)))==1
    database(operation)
