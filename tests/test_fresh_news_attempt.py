"""Explicit operator attempt, same day and ledger; never used by the scheduler."""
import copy
from contextlib import asynccontextmanager
from datetime import timedelta
from decimal import Decimal

import pytest
from test_research import client,database,Redis
from test_nightly_web import NOW
from app.models import ResearchControl,ResearchRun
from app.research import worker,editorial,writing
from app.research.config import ResearchSettings


@pytest.mark.parametrize('mode',['valid','budget','uncertain','used','wrong_day','active'])
def test_fresh_attempt_preserves_history_budget_and_one_shot_guard(client,monkeypatch,mode):
    monkeypatch.setattr(worker,'utcnow',lambda:NOW)
    monkeypatch.setattr(worker,'settings',lambda:ResearchSettings(api_key='offline',daily_usd=Decimal('.20'),monthly_usd=Decimal('10')))
    r=Redis();monkeypatch.setattr(worker,'get_redis',lambda:r)
    calls=[]
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True))
        report={'web_research':{'state':'response','settled':True,'raw':'saved primary'},
                'alternative_web_research':{'state':'response','settled':mode!='uncertain','raw':'saved alternative'},
                'manual_news_retry':{'result':{'new_article_id':None,'status':'skipped'}}}
        if mode=='used':report['manual_news_retry']['fresh_authorized']=True
        original=copy.deepcopy(report)
        amount=150000 if mode=='budget' else 83281
        run=ResearchRun(editorial_date=NOW.date()-(timedelta(days=1) if mode=='wrong_day' else timedelta()),
                        status='running' if mode=='active' else 'skipped',reason='no_verified_news',reserved_microusd=amount,report=report,finished_at=NOW)
        db.add(run);await db.commit()
        @asynccontextmanager
        async def session():yield db
        monkeypatch.setattr(worker,'get_sessionmaker',lambda:session)
        async def execute(db,row,config,redis,token,**kwargs):
            calls.append(kwargs)
            assert row.reserved_microusd==amount
            assert row.report['prior_attempts'][0]['report']==original
            assert row.report['manual_news_retry']['fresh_authorized']
            assert 'web_research' not in row.report
            row.status='skipped';row.reason='no_verified_news';await db.commit()
        monkeypatch.setattr(editorial,'execute',execute)
        if mode=='valid':
            await worker.retry_news(run.id,fresh=True)
            assert calls==[{'max_publications':1,'allow_evergreen':False}]
            assert run.reserved_microusd==amount
            assert run.report['manual_news_retry']['fresh_authorized']
            with pytest.raises(writing.StopRun):await worker.retry_news(run.id,fresh=True)
            assert len(calls)==1
        else:
            with pytest.raises(writing.StopRun):await worker.retry_news(run.id,fresh=True)
            assert not calls and run.report==original and run.reserved_microusd==amount
    database(operation)
