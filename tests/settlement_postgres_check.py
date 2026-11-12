"""Run only against a restored network-isolated PostgreSQL, without API secrets."""
import asyncio,json,os
from datetime import date
from sqlalchemy import select,func
from app.core.db import get_sessionmaker
from app.models import ResearchRun,ResearchControl,GenerationUsage,AuditLog
from app.research.checkpoints import settle_completed
from app.research.config import ResearchSettings
from app.research.worker import reserve
from app.research.writing import StopRun
async def main():
 assert 'rapid_isolated_check' in os.environ['DATABASE_URL']
 cfg=ResearchSettings()
 async with get_sessionmaker()() as db:
  control=await db.get(ResearchControl,1);control.enabled=True
  row=ResearchRun(editorial_date=date(2100,1,1),reserved_microusd=140000,report={})
  db.add(row);await db.flush();rid=row.id
  row.report={'stage_checkpoints':{'fixture':{'state':'response','editorial_date':str(row.editorial_date),
   'ledger_key':'isolated-settlement-race','stage':'Draft','maximum_microusd':30000,
   'usage':{'input_tokens':1000,'output_tokens':1000}}}}
  db.add(GenerationUsage(run_id=rid,model='gpt-5-mini',stage='Draft',request_key='isolated-settlement-race',input_tokens=1000,output_tokens=1000,cached_tokens=0,estimated_microusd=2250))
  await db.commit()
 async def settle():
  async with get_sessionmaker()() as db:
   row=await db.get(ResearchRun,rid);await settle_completed(db,row,cfg)
 await asyncio.gather(settle(),settle())
 async with get_sessionmaker()() as db:
  row=await db.get(ResearchRun,rid);assert row.reserved_microusd==112250
  assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action=='research_reservation_settled',AuditLog.entity_id==rid))==1
 async def spend():
  async with get_sessionmaker()() as db:
   row=await db.get(ResearchRun,rid)
   try:await reserve(db,row,cfg,30000);return 'reserved'
   except StopRun as exc:return str(exc)
 result=await asyncio.gather(spend(),spend())
 assert sorted(result)==['budget_exhausted','reserved'],result
 async with get_sessionmaker()() as db:
  row=await db.get(ResearchRun,rid);assert row.reserved_microusd==142250
 print(json.dumps({'concurrent_settlement':'once','concurrent_reservation':'one_allowed_one_blocked','daily_limit_preserved':True,'model_calls':0}))
asyncio.run(main())
