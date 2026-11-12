"""Privileged retry must never erase spending/history or become a daily retry loop."""
import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from test_research import Redis, client, database, app_override
from app.models import ResearchControl, ResearchRun, utcnow
from app.research import worker, writing


@pytest.mark.parametrize('mode', ['eligible', 'provider', 'published', 'running', 'article', 'yesterday', 'already_retried'])
def test_manual_retry_preserves_history_and_cumulative_budget(client, monkeypatch, mode):
    now = datetime(2026, 10, 24, 12, tzinfo=UTC)
    redis = Redis(); calls = []
    monkeypatch.setenv('OPENAI_API_KEY', 'test-placeholder')
    monkeypatch.setattr(worker, 'utcnow', lambda: now)
    monkeypatch.setattr(worker, 'get_redis', lambda: redis)
    monkeypatch.setattr(worker, 'get_sessionmaker', lambda: lambda: asynccontextmanager(app_override())())
    async def seed(db):
        db.add(ResearchControl(id=1, enabled=True))
        row = ResearchRun(editorial_date=now.date() - timedelta(days=1 if mode == 'yesterday' else 0),
            status='running' if mode == 'running' else 'published' if mode == 'published' else 'skipped',
            reason='provider_unavailable' if mode == 'provider' else 'invalid_evidence',
            finished_at=now, reserved_microusd=34771, report={'versions': [{'validation_error': 'invalid_evidence'}]})
        if mode == 'already_retried': row.report = {'manual_retry': {}}
        if mode == 'article': row.article_id = 999
        db.add(row); await db.flush(); return row.id
    rid = database(seed)
    async def pipeline(db, run, config, *args):
        calls.append(run.id)
        await worker.reserve(db, run, config, 10000)
        raise writing.StopRun('review_rejected')
    monkeypatch.setattr(worker, 'pipeline', pipeline)
    if mode == 'eligible':
        asyncio.run(worker.retry_failed(rid))
        with pytest.raises(writing.StopRun, match='retry_not_eligible'):
            asyncio.run(worker.retry_failed(rid))
    else:
        with pytest.raises(writing.StopRun, match='retry_not_eligible'):
            asyncio.run(worker.retry_failed(rid))
    async def check(db):
        rows = (await db.scalars(select(ResearchRun))).all(); assert len(rows) == 1
        row = rows[0]
        assert row.reserved_microusd == (44771 if mode == 'eligible' else 34771)
        if mode == 'eligible':
            assert row.report['prior_attempts'][0]['report']['versions'][0]['validation_error'] == 'invalid_evidence'
            assert row.report['prior_attempts'][0]['reserved_microusd'] == 34771
            assert row.status == 'skipped' and row.reason == 'review_rejected'
    database(check)
    assert len(calls) == (1 if mode == 'eligible' else 0)
