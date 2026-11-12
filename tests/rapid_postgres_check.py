"""Run explicitly in a restored, network-isolated test database; never production."""
import asyncio,json,os
from datetime import date,datetime,UTC
from sqlalchemy import select,func
from app.core.db import get_sessionmaker
from app.models import ResearchControl,ResearchRun,EditorialCandidate,NewsScan
from app.research.config import ResearchSettings
from app.research.worker import reserve
from app.research.writing import StopRun
from app.research.queue import upsert_event
from app.research.events import identify

async def race_reservations(ids):
    event=asyncio.Event();ready=0
    async def attempt(rid):
        nonlocal ready
        async with get_sessionmaker()() as db:
            row=await db.get(ResearchRun,rid);ready+=1
            if ready==2:event.set()
            await event.wait()
            try:await reserve(db,row,ResearchSettings(),90000);return 'reserved'
            except StopRun as exc:await db.rollback();return str(exc)
    return await asyncio.gather(*(attempt(i) for i in ids))

async def main():
    assert not os.environ.get('OPENAI_API_KEY')
    assert os.environ['DATABASE_URL'].endswith('/rapid_isolated_check')
    async with get_sessionmaker()() as db:
        control=await db.get(ResearchControl,1);control.enabled=True
        day=ResearchRun(editorial_date=date(2099,1,1),status='skipped');db.add(day);await db.commit();rid=day.id
    results=await race_reservations([rid,rid]);assert sorted(results)==['budget_exhausted','reserved'],results
    async with get_sessionmaker()() as db:
        assert (await db.get(ResearchRun,rid)).reserved_microusd==90000
        db.add(ResearchRun(editorial_date=date(2099,2,1),status='skipped',reserved_microusd=4900000))
        a=ResearchRun(editorial_date=date(2099,2,2),status='skipped');b=ResearchRun(editorial_date=date(2099,2,3),status='skipped');db.add_all([a,b]);await db.commit();ids=[a.id,b.id]
    monthly=await race_reservations(ids);assert sorted(monthly)==['budget_exhausted','reserved'],monthly
    stamp=datetime(2099,3,1,tzinfo=UTC)
    docs=[dict(id=1,url='https://openai.com/index/rapid-isolated-fixture',title='OpenAI announces GPT-4o',organization='openai',organization_verified=True,published=stamp.isoformat(),language='en',text='OpenAI announces the GPT-4o multimodal model. '+'Original fixture context about text, images and audio capabilities of the announcement. '*15),
        dict(id=2,url='https://www.microsoft.com/en-us/research/rapid-isolated-fixture',title='OpenAI introduces GPT-4o',organization='microsoft',organization_verified=True,published=stamp.isoformat(),language='en',text='An independent fixture describes GPT-4o. '+'Integration notes discuss service configuration, verification responsibilities and application limitations. '*16)]
    async def upsert(doc):
        async with get_sessionmaker()() as db:return (await upsert_event(db,[doc],identify(doc),stamp)).id
    candidates=await asyncio.gather(*(upsert(d) for d in docs));assert candidates[0]==candidates[1]
    async with get_sessionmaker()() as db:
        candidate=await db.get(EditorialCandidate,candidates[0]);assert candidate.state=='ready' and len(candidate.details['sources'])==2
    async def scan():
        from sqlalchemy.exc import IntegrityError
        async with get_sessionmaker()() as db:
            db.add(NewsScan(window=stamp))
            try:await db.commit();return 'created'
            except IntegrityError:await db.rollback();return 'duplicate'
    scans=await asyncio.gather(scan(),scan());assert sorted(scans)==['created','duplicate']
    print(json.dumps({'postgres_daily_concurrency':results,'postgres_monthly_concurrency':monthly,'concurrent_event_deduplication':True,'concurrent_scan_deduplication':True,'paid_calls':0}))

if __name__=='__main__':asyncio.run(main())
