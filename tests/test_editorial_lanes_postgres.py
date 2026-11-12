"""Explicit isolated PostgreSQL/Redis tests. Never run against application data."""
import asyncio
import os
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select, text, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.models import Base, ResearchRun, ResearchControl, EditorialLaneRun, EditorialCandidate, Article, AuditLog
from app.research import worker, quality, lanes
from app.research.config import ResearchSettings
from app.research.writing import StopRun
from app.modules.articles.schemas import ArticleWrite

pytestmark = pytest.mark.skipif(os.environ.get('FOROIA_ISOLATED_DB')!='lanes-phase12', reason='Dedicated PostgreSQL/Redis required')


def isolated(operation):
    async def main():
        url=os.environ['DATABASE_URL']
        assert url=='postgresql+asyncpg://postgres@127.0.0.1:5432/foroia_lanes_phase12'
        assert not os.environ.get('OPENAI_API_KEY')
        engine=create_async_engine(url,poolclass=NullPool)
        maker=async_sessionmaker(engine,expire_on_commit=False)
        try:
            async with maker() as db:
                assert await db.scalar(text('SELECT current_database()'))=='foroia_lanes_phase12'
                assert await db.scalar(text('SELECT version_num FROM alembic_version'))=='0011_recoverable_editorial'
                for table in reversed(Base.metadata.sorted_tables):await db.execute(table.delete())
                db.add(ResearchControl(id=1,enabled=True));await db.commit()
            await operation(maker)
        finally:await engine.dispose()
    asyncio.run(main())


CONFIG=ResearchSettings(daily_usd=Decimal('.20'),monthly_usd=Decimal('10'),two_lanes=True)


@pytest.mark.parametrize('monthly', [False, True])
def test_atomic_daily_and_monthly_reservations_across_real_connections(monthly):
    async def operation(maker):
        async with maker() as db:
            if monthly:db.add(ResearchRun(editorial_date=date(2099,1,1),reserved_microusd=9850000,report={}))
            run=ResearchRun(editorial_date=date(2099,1,2),reserved_microusd=0 if monthly else 50000,report={})
            db.add(run);await db.commit();rid=run.id
        async def reserve():
            async with maker() as db:
                run=await db.get(ResearchRun,rid)
                try:await worker.reserve(db,run,CONFIG,100000);return 'reserved'
                except StopRun as exc:await db.rollback();return str(exc)
        assert sorted(await asyncio.gather(reserve(),reserve()))==['budget_exhausted','reserved']
        async with maker() as db:
            run=await db.get(ResearchRun,rid)
            assert run.reserved_microusd==(100000 if monthly else 150000)
            assert await db.scalar(select(func.sum(ResearchRun.reserved_microusd)))<=10000000
    isolated(operation)


def test_completed_manual_reservation_settlement_is_atomic():
    from app.models import EditorialExecution,GenerationUsage
    from app.research.executions import settle_execution
    async def operation(maker):
        async with maker() as db:
            r=ResearchRun(editorial_date=date(2099,1,3),reserved_microusd=1200);db.add(r);await db.flush()
            j=EditorialExecution(mode='resume',request_key='atomic-manual-settle',state='completed',run_id=r.id,reserved_microusd=1000,report={},prepared={});db.add(j);await db.flush()
            j.report={'reserved_calls':1,'stage_checkpoints':{'request':{'execution_id':j.id,'stage':'Review','state':'response','ledger_key':'atomic-manual-ledger','maximum_microusd':1000,'usage':{'input_tokens':10,'output_tokens':10}}}}
            db.add(GenerationUsage(run_id=r.id,request_key='atomic-manual-ledger',stage='Review',model='gpt-5-mini',input_tokens=10,output_tokens=10,cached_tokens=0,estimated_microusd=20))
            await db.commit();jid=j.id;rid=r.id
        async def settle():
            async with maker() as db:await settle_execution(db,await db.get(EditorialExecution,jid))
        await asyncio.gather(settle(),settle())
        async with maker() as db:
            assert (await db.get(ResearchRun,rid)).reserved_microusd==220
            assert (await db.get(EditorialExecution,jid)).reserved_microusd==20
            assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action=='execution_reservation_settled'))==1
    isolated(operation)


def test_practical_headroom_and_lane_claims_are_atomic_with_real_redis():
    async def operation(maker):
        from redis.asyncio import Redis
        redis=Redis.from_url('redis://127.0.0.1:6379/0')
        await redis.set(worker.LOCK,b'owner',ex=120)
        try:
            async with maker() as db:
                parent=ResearchRun(editorial_date=date(2099,2,1),reserved_microusd=100000,
                                   report={'practical_headroom_microusd':40000})
                db.add(parent);await db.commit();rid=parent.id
            async def claim():
                async with maker() as db:
                    return bool(await lanes.claim(db,await db.get(ResearchRun,rid),'news',redis,b'owner'))
            assert sorted(await asyncio.gather(claim(),claim()))==[False,True]
            async with maker() as db:
                parent=await db.get(ResearchRun,rid)
                row=await db.scalar(select(EditorialLaneRun))
                with pytest.raises(StopRun,match='budget_exhausted'):
                    await worker.reserve(db,lanes.LaneRun(row,parent),CONFIG,70000)
                await db.rollback()
            async with maker() as db:
                parent=await db.get(ResearchRun,rid)
                practical=await lanes.claim(db,parent,'evergreen',redis,b'owner')
                await worker.reserve(db,practical,CONFIG,70000)
                assert parent.reserved_microusd==170000
                assert await db.scalar(select(func.count(EditorialLaneRun.id)))==2
                # A stale owner may not claim another lane after ownership changes.
                await redis.set(worker.LOCK,b'new-owner',ex=120)
                with pytest.raises(StopRun,match='lock_lost'):await lanes.claim(db,parent,'news',redis,b'owner')
        finally:await redis.aclose()
    isolated(operation)


def test_final_publication_transaction_prevents_racing_duplicate_candidate(monkeypatch):
    """Focused final-commit test; evidence/model checks are tested separately."""
    async def operation(maker):
        from redis.asyncio import Redis
        redis=Redis.from_url('redis://127.0.0.1:6379/0')
        await redis.set(worker.LOCK,b'owner',ex=120)
        try:
            async with maker() as db:
                candidate=EditorialCandidate(fingerprint='p'*64,engine='news',kind='news',state='generating',
                    topic='Isolated concurrent publication',intent='Test final transaction',keyword='isolated test',section='actualidad',details={})
                a=ResearchRun(editorial_date=date(2099,3,1),report={});b=ResearchRun(editorial_date=date(2099,3,2),report={})
                db.add_all([candidate,a,b]);await db.commit();cid=candidate.id;ids=[a.id,b.id]
            barrier=asyncio.Barrier(2)
            async def prepare(db,run,config,evidence,existing,budget,generator,**kw):
                await budget(1000)
                data=ArticleWrite(slug='isolated-publication-'+str(run.id),title='Isolated publication transaction',
                    summary='An isolated concurrency test for the final publication transaction.',body='Verified isolated test. '*30,
                    section='actualidad',author_name='Isolated test',sources=[{'title':'Official fixture','url':'https://openai.com/index/isolated-fixture','language':'en'}])
                article=Article(**data.model_dump(mode='json'),status='draft');db.add(article);await db.flush()
                run.article_id=article.id;await db.commit();await barrier.wait()
                return article,data
            monkeypatch.setattr(quality,'prepare',prepare)
            async def collector(now,urls):return [{'organization':'a'},{'organization':'b'}],{}
            async def publish(rid):
                async with maker() as db:
                    try:
                        await worker.pipeline(db,await db.get(ResearchRun,rid),CONFIG,redis,b'owner',collector=collector,
                            policy={'kind':'news','min_organizations':0},candidate=await db.get(EditorialCandidate,cid))
                        return 'published'
                    except StopRun as exc:await db.rollback();return str(exc)
            assert sorted(await asyncio.gather(*(publish(rid) for rid in ids)))==['duplicate_publication','published']
            async with maker() as db:
                assert await db.scalar(select(func.count(Article.id)).where(Article.status=='published'))==1
                assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action=='auto_publish'))==1
        finally:await redis.aclose()
    isolated(operation)


def test_additive_migration_round_trip_preserves_content_and_budget():
    async def operation(maker):
        from pathlib import Path
        from alembic import command
        from alembic.config import Config
        async with maker() as db:
            db.add(ResearchRun(editorial_date=date(2099,4,1),reserved_microusd=12345,report={'preserve':True}))
            db.add(Article(slug='migration-preservation',title='Keep existing content',summary='Preserve data during additive migration checks.',
                           body='Existing isolated article',section='tutoriales',author_name='Isolated test',sources=[],status='published',
                           published_at=datetime(2099,4,1,tzinfo=UTC)))
            await db.commit()
        root=Path(worker.__file__).resolve().parents[2]
        config=Config(str(root/'alembic.ini'));config.set_main_option('script_location',str(root/'alembic'))
        await asyncio.to_thread(command.downgrade,config,'0009_article_media')
        await asyncio.to_thread(command.upgrade,config,'head')
        async with maker() as db:
            assert await db.scalar(select(ResearchRun.reserved_microusd))==12345
            assert await db.scalar(select(Article.slug))=='migration-preservation'
    isolated(operation)


def test_concurrent_lane_settlement_releases_a_confirmed_reservation_once():
    async def operation(maker):
        from app.models import GenerationUsage
        from app.research.checkpoints import settle_completed
        async with maker() as db:
            parent=ResearchRun(editorial_date=date(2099,5,1),reserved_microusd=50000,report={})
            db.add(parent);await db.flush()
            row=EditorialLaneRun(run_id=parent.id,engine='news',report={'stage_checkpoints':{'request':{
                'state':'response','editorial_date':'2099-05-01','ledger_key':'settlement-key',
                'maximum_microusd':20000,'stage':'Draft','usage':{'input_tokens':100,'output_tokens':200}}}})
            db.add(row)
            db.add(GenerationUsage(run_id=parent.id,candidate_id=None,stage='Draft',model=CONFIG.model,
                request_key='settlement-key',input_tokens=100,output_tokens=200,cached_tokens=0,estimated_microusd=425))
            await db.commit();rid=parent.id;lid=row.id
        async def settle():
            async with maker() as db:
                await settle_completed(db,lanes.LaneRun(await db.get(EditorialLaneRun,lid),await db.get(ResearchRun,rid)),CONFIG)
        await asyncio.gather(settle(),settle())
        async with maker() as db:
            parent=await db.get(ResearchRun,rid)
            assert parent.reserved_microusd==30425
            assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action=='research_reservation_settled'))==1
            with pytest.raises(ValueError):await worker.reserve(db,parent,CONFIG,-1)
    isolated(operation)


def test_second_practical_slot_is_unique_under_concurrent_claims():
    async def operation(maker):
        from redis.asyncio import Redis
        redis=Redis.from_url('redis://127.0.0.1:6379/0');await redis.set(worker.LOCK,b'owner',ex=120)
        try:
            async with maker() as db:
                parent=ResearchRun(editorial_date=date(2099,6,1),report={});db.add(parent);await db.commit();rid=parent.id
            async def claim(slot):
                async with maker() as db:return bool(await lanes.claim(db,await db.get(ResearchRun,rid),'evergreen',redis,b'owner',slot))
            results=await asyncio.gather(claim(1),claim(1),claim(2),claim(2))
            assert sum(results)==2
            async with maker() as db:
                assert (await db.scalars(select(EditorialLaneRun.slot).order_by(EditorialLaneRun.slot))).all()==[1,2]
        finally:await redis.aclose()
    isolated(operation)


@pytest.mark.parametrize('monthly',[False,True])
def test_proposed_caps_and_two_practical_reserves_remain_atomic(monthly):
    async def operation(maker):
        config=ResearchSettings(daily_usd='.50',monthly_usd='15',two_lanes=True,practical_publications=2)
        async with maker() as db:
            if monthly:db.add(ResearchRun(editorial_date=date(2099,7,1),reserved_microusd=14600000,report={}))
            parent=ResearchRun(editorial_date=date(2099,7,2),report={'practical_headroom_microusd':80000});db.add(parent);await db.flush()
            lane=EditorialLaneRun(run_id=parent.id,engine='news',slot=1,report={});db.add(lane);await db.commit();rid=parent.id;lid=lane.id
        async def reserve():
            async with maker() as db:
                try:
                    await worker.reserve(db,lanes.LaneRun(await db.get(EditorialLaneRun,lid),await db.get(ResearchRun,rid)),config,270000)
                    return 'reserved'
                except StopRun as exc:await db.rollback();return str(exc)
        assert sorted(await asyncio.gather(reserve(),reserve()))==['budget_exhausted','reserved']
        async with maker() as db:
            assert (await db.get(ResearchRun,rid)).reserved_microusd==270000
            assert await db.scalar(select(func.sum(ResearchRun.reserved_microusd)))<=15000000
    isolated(operation)


def test_two_distinct_practicals_cannot_race_past_daily_quota(monkeypatch):
    async def operation(maker):
        from redis.asyncio import Redis
        from app.models import utcnow
        redis=Redis.from_url('redis://127.0.0.1:6379/0');await redis.set(worker.LOCK,b'owner',ex=120)
        config=ResearchSettings(two_lanes=True,practical_publications=2,daily_usd='.50',monthly_usd='15')
        try:
            async with maker() as db:
                old=Article(slug='prior-practical',title='A prior practical',summary='An existing valid practical article.',body='Existing content',section='programacion',author_name='Fixture',sources=[],status='published',published_at=utcnow())
                db.add(old);await db.flush()
                prior=EditorialCandidate(fingerprint='a'*64,engine='evergreen',kind='tutorial',topic='Prior',intent='Existing',keyword='Existing',section='programacion',state='published',article_id=old.id,published_at=utcnow(),details={})
                run=ResearchRun(editorial_date=utcnow().date(),report={});db.add_all([prior,run]);await db.flush()
                candidates=[EditorialCandidate(fingerprint=str(i)*64,engine='evergreen',kind='tutorial',topic='Candidate '+str(i),intent='Isolated test',keyword='isolated task',section='programacion',state='generating',details={}) for i in [1,2]]
                db.add_all(candidates);await db.commit();ids=[c.id for c in candidates];rid=run.id
            barrier=asyncio.Barrier(2)
            async def prepare(db,workspace,config,evidence,existing,budget,generator,**kw):
                cid=kw['policy']['candidate_id']
                data=ArticleWrite(slug='quota-isolated-'+str(cid),title='Practical isolated task '+str(cid),summary='A valid isolated practical publication transaction.',body='Verified isolated content '*30,section='programacion',author_name='Fixture',sources=[{'title':'Official fixture','url':'https://docs.python.org/3/library/json.html','language':'en'}])
                article=Article(**data.model_dump(mode='json'),status='draft');db.add(article);await db.flush();workspace.article_id=article.id;await db.commit();await barrier.wait();return article,data
            monkeypatch.setattr(quality,'prepare',prepare)
            async def collector(now,urls):return [],{}
            async def publish(cid):
                async with maker() as db:
                    # Separate workspaces, shared budget parent.
                    lane=EditorialLaneRun(run_id=rid,engine='evergreen',slot=ids.index(cid)+1,report={});db.add(lane);await db.commit()
                    try:
                        await worker.pipeline(db,lanes.LaneRun(lane,await db.get(ResearchRun,rid)),config,redis,b'owner',collector=collector,
                            policy={'kind':'tutorial','min_organizations':0,'candidate_id':cid},candidate=await db.get(EditorialCandidate,cid))
                        return 'published'
                    except StopRun as exc:await db.rollback();return str(exc)
            assert sorted(await asyncio.gather(*(publish(cid) for cid in ids)))==['daily_publication_limit','published']
            async with maker() as db:assert await db.scalar(select(func.count(Article.id)).where(Article.status=='published'))==2
        finally:await redis.aclose()
    isolated(operation)
