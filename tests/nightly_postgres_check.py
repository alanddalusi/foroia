"""Explicitly run only in a restored network-isolated PostgreSQL; no API key."""
import asyncio
import json
import os
import threading
from datetime import date, datetime, UTC

from sqlalchemy import select, func
from app.core.db import get_sessionmaker
from app.models import ResearchControl, ResearchRun, GenerationUsage
from app.research.config import ResearchSettings
from app.research.night_web import research


class Redis:
    async def get(self,key):return b'owner'


async def race(ids,recovery=False):
    started=threading.Event();released=threading.Event();calls=[]
    def provider(config,payload):
        calls.append(1);started.set()
        assert released.wait(10)
        return '{"candidates":[]}',{'input_tokens':8000,'output_tokens':800,
            '_web':{'search_calls':1,'complete_output':True,'sources':[]}}
    ready=asyncio.Event();count=0
    async def run(rid):
        nonlocal count
        async with get_sessionmaker()() as db:
            row=await db.get(ResearchRun,rid);count+=1
            if count==2:ready.set()
            await ready.wait()
            options={'state_key':'alternative_web_research','stage':'SourceRecovery','headroom_microusd':40000} if recovery else {}
            found,report=await research(db,row,ResearchSettings(),Redis(),b'owner',datetime(2099,6,1,tzinfo=UTC),provider,**options)
            return report.get('reason') or report['state']
    tasks=[asyncio.create_task(run(rid)) for rid in ids]
    try:
        assert await asyncio.to_thread(started.wait,5)
        # The other session must finish its lock/recheck while the call is pending.
        done,pending=await asyncio.wait(tasks,timeout=5,return_when=asyncio.FIRST_COMPLETED)
        assert len(done)==1 and len(pending)==1
    finally:released.set()
    result=await asyncio.gather(*tasks)
    assert len(calls)==1,(calls,result)
    return result


async def main():
    assert not os.environ.get('OPENAI_API_KEY')
    assert os.environ['DATABASE_URL'].endswith('/rapid_isolated_check')
    async with get_sessionmaker()() as db:
        (await db.get(ResearchControl,1)).enabled=True
        run=ResearchRun(editorial_date=date(2099,6,1),reserved_microusd=0,report={})
        db.add(run);await db.commit();rid=run.id
    same=await race([rid,rid])
    assert sorted(same)==['no_candidates_reported','uncertain_search_result'],same
    async with get_sessionmaker()() as db:
        assert (await db.get(ResearchRun,rid)).reserved_microusd==13600
        assert await db.scalar(select(func.count(GenerationUsage.id)).where(GenerationUsage.run_id==rid))==1
        db.add(ResearchRun(editorial_date=date(2099,7,1),reserved_microusd=4940000,report={}))
        a=ResearchRun(editorial_date=date(2099,7,2),reserved_microusd=0,report={})
        b=ResearchRun(editorial_date=date(2099,7,3),reserved_microusd=0,report={})
        db.add_all([a,b]);await db.commit();ids=[a.id,b.id]
    monthly=await race(ids)
    assert sorted(monthly)==['budget_exhausted','no_candidates_reported'],monthly
    async with get_sessionmaker()() as db:
        total=await db.scalar(select(func.sum(ResearchRun.reserved_microusd)).where(ResearchRun.editorial_date>=date(2099,7,1)))
        assert total==4953600
    async with get_sessionmaker()() as db:
        run=ResearchRun(editorial_date=date(2099,8,1),reserved_microusd=0,report={});db.add(run);await db.commit();recovery_id=run.id
    recovery_same=await race([recovery_id,recovery_id],recovery=True)
    assert sorted(recovery_same)==['no_candidates_reported','uncertain_search_result']
    async with get_sessionmaker()() as db:
        assert await db.scalar(select(func.count(GenerationUsage.id)).where(GenerationUsage.run_id==recovery_id,GenerationUsage.stage=='SourceRecovery'))==1
        db.add(ResearchRun(editorial_date=date(2099,9,1),reserved_microusd=4900000,report={}))
        a=ResearchRun(editorial_date=date(2099,9,2),reserved_microusd=0,report={});b=ResearchRun(editorial_date=date(2099,9,3),reserved_microusd=0,report={})
        db.add_all([a,b]);await db.commit();recovery_ids=[a.id,b.id]
    recovery_monthly=await race(recovery_ids,recovery=True)
    assert sorted(recovery_monthly)==['budget_exhausted','no_candidates_reported']
    print(json.dumps({'same_run_single_call':same,'monthly_atomic_budget':monthly,
        'recovery_same_run':recovery_same,'recovery_monthly_headroom':recovery_monthly,
        'usage_ledger_idempotent':True,'settled_cost_microusd':13600,'paid_calls':0,'provider':'simulated'}))


if __name__=='__main__':asyncio.run(main())
