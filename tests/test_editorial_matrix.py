"""All eleven plans through the real coordinator/provider adapter; fake model, isolated DB.

These fixtures establish control-flow and budget compatibility, not live model quality.
"""
import json
from datetime import timedelta
import pytest
from sqlalchemy import select

from test_research import client,database,Redis
from test_editorial_engines import NOW,receipt,docs,no_news,verifier,tutorial_payload
from test_evidence_first import approved_payload
from app.models import ResearchRun,ResearchControl,EditorialCandidate,GenerationUsage,Article
from app.research import editorial,writing,queue,worker
from app.research.blueprints import BLUEPRINTS
from app.research.config import ResearchSettings


def plan_provider(blueprint,calls):
    def provider(config,payload):
        data=json.loads(payload['input']);kind=payload['text']['format']['name'];calls.append(kind)
        assert 'un tema sólido' not in payload['instructions'] or 'dos organizaciones diferentes' not in payload['instructions']
        if kind=='evergreendraft':
            value=tutorial_payload(payload)
            value.update(title=blueprint.topic,slug='plan-'+blueprint.key,section=blueprint.section)
            # Comparisons must actually cite distinct organizations, not merely receive them.
            for i,p in enumerate(value['paragraphs']):
                source=data['sources'][i%len(data['sources'])]
                p['evidence']=[{'fragment_id':source['fragments'][0]['fragment_id']}]
        else:value=approved_payload(payload)
        return json.dumps(value),{'input_tokens':1000,'output_tokens':800,'input_tokens_details':{'cached_tokens':100},'output_tokens_details':{'reasoning_tokens':200}}
    return provider


@pytest.mark.parametrize('blueprint',BLUEPRINTS,ids=lambda b:b.key)
def test_every_plan_can_publish_with_valid_evidence_within_daily_budget(client,tmp_path,monkeypatch,blueprint):
    monkeypatch.setattr(editorial,'utcnow',lambda:NOW)
    calls=[]
    monkeypatch.setattr(writing,'call',plan_provider(blueprint,calls))
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True));await queue.seed_evergreen(db)
        candidates=(await db.scalars(select(EditorialCandidate))).all()
        target=next(c for c in candidates if c.details['blueprint']==blueprint.key)
        target.priority=100
        assert target.attempts==0
        # Reopening the DB session represents a worker restart, not a new queue.
        await db.commit();await db.close()
        run=ResearchRun(editorial_date=NOW.date());db.add(run);await db.commit()
        redis=Redis();redis.value=b'owner'
        await editorial.execute(db,run,ResearchSettings(),redis,b'owner',news_collector=no_news,doc_loader=docs,
            verifier=verifier,receipt_path=receipt(tmp_path))
        published=await db.get(EditorialCandidate,target.id,populate_existing=True)
        assert published.state=='published' and published.attempts==1,run.report
        article=await db.get(Article,published.article_id)
        assert article.status=='published' and article.section==blueprint.section
        assert len(article.sources)>=(2 if blueprint.kind=='comparison' else 1)
        assert 0<run.reserved_microusd<150000
        assert len((await db.scalars(select(GenerationUsage))).all())==2
        assert published.details['usage_events'][-1]['reasoning_tokens']==200
        assert run.reason=='quality_checks_passed'
    database(operation)
    assert calls==['evergreendraft','groundedreview']


def test_usage_missing_cached_and_reasoning_are_not_invented_or_double_counted(client):
    async def operation(db):
        await queue.seed_evergreen(db);candidate=await db.scalar(select(EditorialCandidate))
        run=ResearchRun(editorial_date=NOW.date(),reserved_microusd=30000);db.add(run);await db.commit()
        await editorial.usage_sink(db,run,candidate,ResearchSettings(),'Review',{})
        assert candidate.details['unreported_usage_calls']==1
        assert (await db.scalars(select(GenerationUsage))).all()==[]
        await editorial.usage_sink(db,run,candidate,ResearchSettings(),'Review',{'input_tokens':1000,'output_tokens':1000,
            'input_tokens_details':{'cached_tokens':800},'output_tokens_details':{'reasoning_tokens':600}})
        row=await db.scalar(select(GenerationUsage))
        assert row.estimated_microusd==2070  # 200*.25 + 800*.025 + 1000*2; reasoning already in output.
        assert run.reserved_microusd==30000
    database(operation)


def test_persistent_sitemap_failure_withdraws_after_three_free_checks(client,monkeypatch):
    from test_articles_api import article as article_payload
    from app.research.publication import article_snapshot,verify_candidate,PublicationError
    def forbidden(*args):pytest.fail('Verification must never call the model')
    monkeypatch.setattr(writing,'call',forbidden)
    async def missing(snapshot,page):raise PublicationError('publication_missing_sitemap',True)
    async def operation(db):
        article=Article(**article_payload(),status='published',published_at=NOW);db.add(article);await db.flush()
        row=EditorialCandidate(fingerprint='e'*64,engine='evergreen',kind='guide',topic='Verified guide',section='tutoriales',
            intent='A practical task',keyword='practical task',state='needs_verification',article_id=article.id,attempts=1,
            details={'publication_snapshot':article_snapshot(article)})
        db.add(row);await db.commit()
        for attempt in range(3):
            assert not await verify_candidate(db,row,missing,NOW+timedelta(seconds=30*attempt))
            if attempt<2:assert row.state=='needs_verification' and article.status=='published'
        assert article.status=='archived' and row.state=='technical_error' and row.details['verification_attempts']==3
    database(operation)


def test_scheduler_runs_evergreen_at_madrid_time_once_after_restart(client,tmp_path,monkeypatch,capsys):
    from contextlib import asynccontextmanager
    from pydantic import SecretStr
    from test_editorial_engines import provider_factory
    # Winter time: 21:30 UTC is 22:30 Madrid; no forced tick.
    stamp=NOW.replace(day=25,hour=21,minute=29,second=59)
    redis=Redis();calls=[]
    config=ResearchSettings(api_key=SecretStr('offline-test'))
    monkeypatch.setattr(worker,'utcnow',lambda:stamp)
    monkeypatch.setattr(editorial,'utcnow',lambda:stamp)
    monkeypatch.setattr(worker,'settings',lambda:config)
    monkeypatch.setattr(worker,'get_redis',lambda:redis)
    monkeypatch.setattr(writing,'call',provider_factory(calls))
    execute=editorial.execute
    async def coordinated(db,run,config,redis,token):
        await execute(db,run,config,redis,token,news_collector=no_news,doc_loader=docs,verifier=verifier,receipt_path=receipt(tmp_path,stamp))
    monkeypatch.setattr(editorial,'execute',coordinated)
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True));await queue.seed_evergreen(db)
        @asynccontextmanager
        async def session():yield db
        monkeypatch.setattr(worker,'get_sessionmaker',lambda:session)
        await worker.tick();assert not calls
        nonlocal stamp
        stamp+=timedelta(seconds=1)
        await worker.tick()
        assert len(calls)==2
        await db.close()
        await worker.tick();assert len(calls)==2
        rows=(await db.scalars(select(EditorialCandidate))).all()
        assert len(rows)==len(BLUEPRINTS) and sum(c.state=='published' for c in rows)==1
    database(operation)
    output=capsys.readouterr().out
    assert 'editorial_run_started' in output and 'editorial_run_finished' in output
