"""Sin servicios externos ni gasto: evidencias, permisos, presupuesto y recuperación."""
import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from test_articles_api import client, AUTH
from test_accounts_api import account_client, database, app_override, seed_user, session
from app.models import Article, ResearchControl, ResearchRun
from app.research import sources, worker, writing
from app.research.config import ResearchSettings, due


QUOTE = 'The new open model can be downloaded and used locally by developers.'
EVIDENCE = [{'id': i, 'url': url, 'title': 'Local inference with open models', 'language': 'en',
             'organization': org, 'organization_verified': True, 'published': '2026-10-21T12:00:00+00:00',
             'text': QUOTE + (' Deployment notes explain memory allocation, processor setup and installation requirements.' if i == 1
                             else ' Independent documentation discusses offline workflows, dataset evaluation and reproducible application examples.') * 25}
            for i, url, org in [(1, 'https://openai.com/news/model', 'openai'), (2, 'https://huggingface.co/blog/model', 'huggingface')]]


def draft():
    text = ('El anuncio abre una opción para quienes quieren trabajar con modelos en su equipo. '
            'Antes de incorporarlo a un proyecto conviene consultar la documentación original y '
            'valorar los requisitos del entorno. Descargar el modelo permite explorar su uso local, '
            'pero esa posibilidad no demuestra que funcione bien para cualquier tarea. ')
    return writing.Draft(title='Un modelo abierto para explorar en tu equipo', slug='modelo-abierto-equipo',
        summary='Qué supone poder descargar un modelo abierto y qué conviene comprobar antes de incorporarlo a un proyecto.',
        section='actualidad', paragraphs=[writing.Paragraph(heading=h, text=t, evidence=[writing.Citation(source_id=i % 2 + 1, quote=QUOTE)])
            for i, (h,t) in enumerate(zip(['Qué cambia', 'A quién ayuda', 'Cómo empezar', 'Qué queda por comprobar'],[
                text,
                'La descarga está orientada a desarrolladores que necesitan trabajar con una ejecución local. Esa opción puede servir para estudiar una integración sin confundir el acceso a los archivos con una garantía sobre la calidad de las respuestas. Conviene delimitar primero el caso de uso y consultar las condiciones documentadas.',
                'El primer paso consiste en revisar la documentación del proyecto y los requisitos del entorno. La posibilidad de utilizar el modelo localmente no determina por sí sola qué recursos harán falta para una aplicación concreta. Cada equipo debe preparar su propio procedimiento de evaluación antes de incorporarlo a un servicio.',
                'Queda por evaluar el comportamiento en las tareas del lector. Este artículo explica lo que permite la distribución anunciada y no aporta mediciones propias ni experiencias inventadas. Distinguir esas dos cosas ayuda a decidir qué información debe verificarse antes de utilizar el modelo con datos de un proyecto.'
            ]))])


def review(approved=True):
    return writing.Review(approved=approved, supported=True, useful=True, original=True, spanish=True,
                         no_invented_experience=True, safe_topic=True, natural=True,non_repetitive=True,well_structured=True,attribution_clear=True,reasons=[] if approved else ['Falta corroboración.'])


@pytest.mark.parametrize('url', ['http://openai.com/news', 'https://localhost/x', 'https://127.0.0.1/x',
    'https://openai.com.evil.test/x', 'https://user:pass@openai.com/x', 'https://openai.com:8443/x', 'https://openai.com/\nx'])
def test_fetch_allowlist(url):
    with pytest.raises((sources.SourceError, ValueError)):
        sources.canonical(url)


def test_dns_rebinding_and_mixed_addresses(monkeypatch):
    monkeypatch.setattr(sources.socket, 'getaddrinfo', lambda *a, **k: [(None, None, None, None, ('8.8.8.8', 443)), (None, None, None, None, ('127.0.0.1', 443))])
    with pytest.raises(sources.SourceError):
        sources.public_addresses('openai.com')


@pytest.mark.parametrize('mode', ['pinned', 'redirect', 'large'])
def test_fetch_pins_socket_and_checks_every_redirect(monkeypatch, mode):
    connects = []
    monkeypatch.setattr(sources, 'public_addresses', lambda host: ['8.8.8.8'])
    monkeypatch.setattr(sources.socket, 'create_connection', lambda address, *args: connects.append(address))
    class Response:
        status = 302 if mode == 'redirect' else 200
        def getheader(self, key, default=None):
            return {'Location': 'https://127.0.0.1/private', 'Content-Type': 'text/html'}.get(key, default)
        def read(self, limit): return b'x' * (sources.MAX_BYTES + 1) if mode == 'large' else b'<p>Public text</p>'
    class Connection:
        def __init__(self, host, **kwargs): assert host == 'openai.com'
        def request(self, *args, **kwargs): self._create_connection(('openai.com', 443), 12)
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(sources.http.client, 'HTTPSConnection', Connection)
    if mode == 'pinned': assert sources.fetch('https://openai.com/news/a')[1] == b'<p>Public text</p>'
    else:
        with pytest.raises(sources.SourceError): sources.fetch('https://openai.com/news/a')
    assert connects == [('8.8.8.8', 443)]


def test_xml_and_date_window():
    now = datetime(2026, 10, 21, 12, tzinfo=UTC)
    xml = b'<rss><channel><item><title>Model</title><link>https://openai.com/news/a?utm=x</link><pubDate>Wed, 21 Oct 2026 10:00:00 GMT</pubDate></item></channel></rss>'
    rows = sources.parse_feed(xml, sources.FEEDS[0], now)
    assert rows[0]['url'] == 'https://openai.com/news/a'
    assert sources.parse_feed(xml, sources.FEEDS[0], now + timedelta(days=3)) == []
    with pytest.raises(sources.SourceError):
        sources.parse_feed(b'<!DOCTYPE rss [<!ENTITY x "a">]><rss/>', sources.FEEDS[0], now)


@pytest.mark.parametrize('utc_hour,expected', [(20, True), (19, False)])
def test_schedule_summer(utc_hour, expected):
    assert bool(due(datetime(2026, 7, 20, utc_hour, 30, tzinfo=UTC), ResearchSettings())) == expected


def test_schedule_winter_and_fallback():
    config = ResearchSettings()
    assert due(datetime(2026, 12, 20, 21, 30, tzinfo=UTC), config)
    assert due(datetime(2026, 12, 20, 20, 30, tzinfo=UTC), config) is None
    early = ResearchSettings(at='02:30')
    assert due(datetime(2026, 10, 25, 0, 30, tzinfo=UTC), early) == due(datetime(2026, 10, 25, 1, 30, tzinfo=UTC), early)


@pytest.mark.parametrize('change,reason', [('quote', 'invalid_evidence'), ('organization', 'insufficient_independent_sources'), ('number', 'unsupported_number'), ('duplicate', 'duplicate_topic')])
def test_quality_rejects(change, reason):
    d = draft()
    evidence = [dict(s) for s in EVIDENCE]
    existing = []
    if change == 'quote': d.paragraphs[0].evidence[0].quote = 'This invented quotation does not occur in the source document.'
    if change == 'organization': evidence[1]['organization'] = evidence[0]['organization']
    if change == 'number': d.paragraphs[0].text += ' Tiene 987 parámetros.'
    if change == 'duplicate': existing = [SimpleNamespace(title=d.title, body='Otro texto')]
    with pytest.raises(writing.StopRun, match=reason): writing.validate_draft(d, evidence, existing)


def test_transparency_and_valid_article():
    article = writing.validate_draft(draft(), EVIDENCE, [])
    assert 'Sin revisión humana previa' in article.body
    assert 'automatizada' in article.author_name
    assert len(article.sources) == 2


def test_review_context_preserves_original_citations():
    proposal = draft()
    proposal.paragraphs[0].evidence[0].quote = QUOTE.lower()
    context = writing.evidence_context(proposal, EVIDENCE)
    assert len(context) == 2
    assert all(QUOTE in row['text'] for row in context)
    assert 'NO exijas citas dentro del título' in writing.REVIEW_INSTRUCTIONS


@pytest.mark.parametrize('field,value', [('summary', 'a' * 301), ('title', 'a' * 181), ('slug', 'URL no valida')])
def test_generation_schema_matches_blog_metadata_limits(field, value):
    data = draft().model_dump()
    data[field] = value
    with pytest.raises(ValueError): writing.Draft.model_validate(data)


@pytest.mark.parametrize('mode', ['fixed', 'still_wrong', 'invalid_citation', 'provider_error', 'budget', 'changed', 'unsafe', 'incomplete_review'])
def test_automatic_correction_is_bounded_and_rechecks(client, mode):
    async def run(db):
        db.add(ResearchControl(id=1, enabled=True))
        row = ResearchRun(editorial_date=datetime(2026, 10, 21).date())
        db.add(row); await db.commit()
        redis = Redis(); redis.value = b'owner'
        calls = []
        async def collect(now, urls): return EVIDENCE, {'candidate_count': 2}
        async def generate(config, schema, instructions, data, reserve):
            await reserve(10000)
            calls.append(schema)
            if schema is writing.Draft:
                correction = calls.count(writing.Draft) == 2
                if correction:
                    assert 'errors' in data and data['errors']['code']
                    if mode == 'provider_error': raise writing.StopRun('provider_unavailable')
                    if mode == 'changed':
                        item = await db.scalar(select(Article))
                        item.body = 'Edición manual que la IA debe conservar'; await db.commit()
                result = draft()
                if correction: result.title = 'Modelo abierto: una explicación con cifras corregidas'
                if mode == 'invalid_citation' and not correction:
                    result.paragraphs[0].evidence[0].quote = 'An invented quotation which cannot be found anywhere in the sources.'
                return result
            if mode == 'unsafe':
                return review(False).model_copy(update={'safe_topic': False})
            if mode == 'incomplete_review' and calls.count(writing.Review) == 2:
                raise writing.StopRun('incomplete_generation')
            return review(mode != 'still_wrong' and (calls.count(writing.Review) > 1 or mode == 'invalid_citation'))
        config = ResearchSettings(daily_usd=Decimal('.025') if mode == 'budget' else Decimal('.15'))
        if mode in {'fixed', 'invalid_citation'}:
            await worker.pipeline(db, row, config, redis, b'owner', collect, generate)
        else:
            with pytest.raises(writing.StopRun): await worker.pipeline(db, row, config, redis, b'owner', collect, generate)
        items = (await db.scalars(select(Article))).all()
        assert len(items) == 1
        assert items[0].status == ('published' if mode in {'fixed', 'invalid_citation'} else 'draft')
        assert row.report.get('corrections_used', 0) == (0 if mode in {'unsafe','budget'} else 1)
        assert len(calls) <= 4
        if mode == 'changed': assert items[0].body == 'Edición manual que la IA debe conservar'
        if mode == 'budget': assert len(calls) == 2 and row.reserved_microusd == 20000
        if mode == 'incomplete_review': assert row.report['pending_review'] and row.report['proposal'] == row.report['evidence']
        if mode == 'fixed':
            assert calls == [writing.Draft, writing.Review, writing.Draft, writing.Review]
            assert len(row.report['versions']) == 2 and row.report['review']['approved']
    database(run)


def test_resume_rejected_article_corrects_same_article_once(client):
    async def run(db):
        db.add(ResearchControl(id=1, enabled=True))
        row = ResearchRun(editorial_date=datetime(2026, 10, 21).date())
        db.add(row); await db.commit()
        redis = Redis(); redis.value = b'owner'
        async def collect(now, urls): return EVIDENCE, {}
        async def first(config, schema, instructions, data, reserve):
            await reserve(10000)
            return draft() if schema is writing.Draft else review(False)
        with pytest.raises(writing.StopRun, match='review_rejected'):
            await worker.pipeline(db, row, ResearchSettings(max_corrections=0), redis, b'owner', collect, first)
        article_id = row.article_id
        calls = []
        async def correction(config, schema, instructions, data, reserve):
            await reserve(10000); calls.append(schema)
            return draft() if schema is writing.Draft else review(True)
        await worker.pipeline(db, row, ResearchSettings(), redis, b'owner', collect, correction, resume=True)
        assert row.article_id == article_id and row.status == 'published'
        assert calls == [writing.Draft, writing.Review]
        assert row.reserved_microusd == 40000
        with pytest.raises(writing.StopRun, match='correction_limit_reached'):
            await worker.pipeline(db, row, ResearchSettings(), redis, b'owner', collect, correction, resume=True)
        assert len(calls) == 2
    database(run)


def test_pending_review_resumes_without_redrafting(client):
    async def run(db):
        db.add(ResearchControl(id=1, enabled=True))
        row = ResearchRun(editorial_date=datetime(2026, 10, 21).date())
        db.add(row); await db.commit()
        redis = Redis(); redis.value = b'owner'
        async def collect(now, urls): return EVIDENCE, {}
        async def first(config, schema, instructions, data, reserve):
            await reserve(10000)
            if schema is writing.Draft: return draft()
            raise writing.StopRun('incomplete_generation')
        with pytest.raises(writing.StopRun): await worker.pipeline(db, row, ResearchSettings(), redis, b'owner', collect, first)
        aid = row.article_id
        async def finish(config, schema, instructions, data, reserve):
            assert schema is writing.Review and config.max_output_tokens == writing.REVIEW_MAX_OUTPUT_TOKENS
            await reserve(10000); return review(True)
        await worker.pipeline(db, row, ResearchSettings(), redis, b'owner', collect, finish, resume='review')
        assert row.status == 'published' and row.article_id == aid
        assert not row.report['pending_review'] and row.reserved_microusd == 30000
    database(run)


def test_restore_fetches_all_cited_sources_but_ignores_unused_failure(monkeypatch):
    metadata = [dict(s) for s in EVIDENCE] + [dict(EVIDENCE[0], id=3, url='https://openai.com/unavailable')]
    # This regression covers legacy expedients without the byline verification flag.
    for source in metadata: source.pop('organization_verified', None)
    fetched = []
    def fetch(url):
        fetched.append(url)
        if url.endswith('unavailable'):
            raise sources.SourceError('Unavailable')
        return url, b'<p>Verified original evidence</p>'
    monkeypatch.setattr(sources, 'fetch', fetch)
    now = datetime(2026, 10, 22, 12, tzinfo=UTC)
    rows, stats = asyncio.run(sources.restore(metadata, now, {1, 2}))
    assert [s['id'] for s in rows] == [1, 2] and len(fetched) == 2
    assert stats['resumed_review']
    with pytest.raises(sources.SourceError):
        asyncio.run(sources.restore(metadata, now, {1, 3}))
    with pytest.raises(sources.SourceError):
        asyncio.run(sources.restore(metadata, now, {1, 99}))


def test_carry_review_retains_original_budget_and_only_once(client):
    from app.models import utcnow
    async def run(db):
        old = ResearchRun(editorial_date=utcnow().date() - timedelta(days=1), status='draft', reason='incomplete_generation', reserved_microusd=140000)
        db.add(old); await db.commit()
        from test_articles_api import article as article_payload
        item = Article(**article_payload(), status='draft'); db.add(item); await db.flush()
        old.article_id = item.id
        old.report = {'pending_review': True, 'proposal': draft().model_dump(), 'evidence': draft().model_dump(), 'sources': EVIDENCE, 'corrections_used': 1}
        row = ResearchRun(editorial_date=utcnow().date()); db.add(row); await db.flush()
        assert await worker.carry_review(db, row)
        await db.commit()
        assert row.article_id == item.id and row.reserved_microusd == 0
        assert old.reserved_microusd == 140000 and old.report['carried_to_run'] == row.id
        row.status, row.reason = 'draft', 'incomplete_generation'
        next_row = ResearchRun(editorial_date=utcnow().date() + timedelta(days=1)); db.add(next_row); await db.flush()
        assert not await worker.carry_review(db, next_row)
    database(run)


class Redis:
    def __init__(self): self.value = None
    async def set(self, key, value, **kwargs):
        if key.endswith('heartbeat'): return True
        if self.value is not None: return False
        self.value = value; return True
    async def get(self, key): return self.value
    async def eval(self, script, count, key, token):
        if self.value == token: self.value = None


@pytest.mark.parametrize('mode', ['publish', 'review', 'reject', 'budget', 'lost_lock', 'changed', 'paused'])
def test_pipeline_transaction_and_rejected_visibility(client, mode):
    async def run(db):
        db.add(ResearchControl(id=1, enabled=True))
        row = ResearchRun(editorial_date=datetime(2026, 10, 21).date())
        db.add(row); await db.commit()
        redis = Redis(); redis.value = b'owner'
        config = ResearchSettings(max_corrections=0, auto_publish=mode != 'review', daily_usd=Decimal('0') if mode == 'budget' else Decimal('.15'))
        async def collect(now, urls): return EVIDENCE, {'candidate_count': 2, 'fetch_failures': 0}
        async def generate(config, schema, instructions, data, reserve):
            await reserve(10000)
            if schema is writing.Draft: return draft()
            if mode == 'lost_lock': redis.value = b'other'
            if mode == 'changed':
                item = await db.scalar(select(Article))
                item.body = 'Cambios manuales del editor'; await db.commit()
            if mode == 'paused':
                control = await db.get(ResearchControl, 1)
                control.enabled = False; await db.commit()
            return review(mode != 'reject')
        if mode in {'reject', 'budget', 'lost_lock', 'changed', 'paused'}:
            with pytest.raises(writing.StopRun): await worker.pipeline(db, row, config, redis, b'owner', collect, generate)
        else:
            await worker.pipeline(db, row, config, redis, b'owner', collect, generate)
        articles = (await db.scalars(select(Article))).all()
        if mode == 'budget': assert articles == [] and row.reserved_microusd == 0
        else:
            expected = 'published' if mode == 'publish' else 'review' if mode == 'review' else 'draft'
            assert articles[0].status == expected
            assert row.reserved_microusd == 20000
    database(run)


def test_monthly_budget_persists_after_failure(client):
    async def run(db):
        db.add(ResearchControl(id=1, enabled=True))
        db.add(ResearchRun(editorial_date=datetime(2026, 10, 20).date(), reserved_microusd=4_990_000, status='skipped'))
        row = ResearchRun(editorial_date=datetime(2026, 10, 21).date())
        db.add(row); await db.commit()
        with pytest.raises(writing.StopRun, match='budget_exhausted'):
            await worker.reserve(db, row, ResearchSettings(), 10001)
        await worker.reserve(db, row, ResearchSettings(), 10000)
        assert row.reserved_microusd == 10000
    database(run)


def test_invalid_proposal_is_retained_privately_without_article(client):
    async def run(db):
        db.add(ResearchControl(id=1, enabled=True))
        row = ResearchRun(editorial_date=datetime(2026, 10, 21).date())
        db.add(row); await db.commit()
        rid = row.id
        redis = Redis(); redis.value = b'owner'
        async def collect(now, urls): return EVIDENCE, {'candidate_count': 2}
        async def generate(config, schema, instructions, data, reserve):
            await reserve(10000)
            result = draft()
            result.paragraphs[0].evidence[0].quote = 'This quotation was invented and is absent from the evidence.'
            return result
        with pytest.raises(writing.StopRun, match='invalid_evidence'):
            await worker.pipeline(db, row, ResearchSettings(max_corrections=0), redis, b'owner', collect, generate)
        await db.rollback()
        saved = await db.get(ResearchRun, rid, populate_existing=True)
        assert saved.report['proposal']['title'] == draft().title
        assert saved.article_id is None and saved.reserved_microusd == 10000
        assert (await db.scalars(select(Article))).all() == []
    database(run)
    assert client.get('/articles').json()['items'] == []


def test_one_run_after_restart_and_no_repeated_spending(client, monkeypatch):
    redis = Redis(); calls = []
    monkeypatch.setenv('OPENAI_API_KEY', 'test-placeholder-not-a-real-key')
    monkeypatch.setattr(worker, 'get_redis', lambda: redis)
    monkeypatch.setattr(worker, 'get_sessionmaker', lambda: lambda: asynccontextmanager(app_override())())
    async def fail(*args): calls.append(1); raise writing.StopRun('insufficient_sources')
    from app.research import editorial
    monkeypatch.setattr(editorial, 'execute', fail)
    async def seed(db): db.add(ResearchControl(id=1, enabled=True))
    database(seed)
    asyncio.run(worker.tick(force=True)); asyncio.run(worker.tick(force=True))
    assert len(calls) == 1
    async def check(db):
        rows = (await db.scalars(select(ResearchRun))).all()
        assert len(rows) == 1 and rows[0].status == 'skipped'
    database(check)


def test_imported_reservations_preserve_budget_and_allow_next_day(client, monkeypatch):
    redis = Redis(); calls = []
    monkeypatch.setenv('OPENAI_API_KEY', 'test-placeholder-not-a-real-key')
    monkeypatch.setattr(worker, 'utcnow', lambda: datetime(2026, 10, 23, 20, 30, tzinfo=UTC))
    monkeypatch.setattr(worker, 'get_redis', lambda: redis)
    monkeypatch.setattr(worker, 'get_sessionmaker', lambda: lambda: asynccontextmanager(app_override())())
    async def seed(db):
        db.add(ResearchControl(id=1, enabled=True))
        for day, amount in [(21, 146237), (22, 11192)]:
            db.add(ResearchRun(editorial_date=datetime(2026, 10, day).date(), status='skipped',
                reason='migrated_local_budget', reserved_microusd=amount))
    async def pipeline(db, run, *args, **kwargs):
        calls.append(run.editorial_date)
        await worker.reserve(db, run, ResearchSettings(), 10000)
        raise writing.StopRun('insufficient_sources')
    database(seed)
    from app.research import editorial
    monkeypatch.setattr(editorial, 'execute', pipeline)
    asyncio.run(worker.tick()); asyncio.run(worker.tick())
    assert calls == [datetime(2026, 10, 23).date()]
    async def check(db):
        rows = (await db.scalars(select(ResearchRun).order_by(ResearchRun.editorial_date))).all()
        assert len(rows) == 3
        assert [r.reserved_microusd for r in rows] == [146237, 11192, 10000]
        assert rows[0].reason == rows[1].reason == 'migrated_local_budget'
    database(check)


def test_private_api_and_pause(account_client, monkeypatch):
    from app.research import routes
    monkeypatch.setattr(routes, 'get_redis', lambda: Redis())
    assert account_client.get('/editorial/research').status_code == 401
    seed_user(role='member')
    assert account_client.get('/editorial/research', headers=session(account_client)).status_code == 403
    seed_user('editor@example.test', role='editor')
    headers = session(account_client, 'editor@example.test')
    async def seed(db): db.add(ResearchControl(id=1, enabled=True))
    database(seed)
    response = account_client.get('/editorial/research', headers=headers)
    assert response.status_code == 200 and 'api_key' not in response.text
    assert response.headers['cache-control'] == 'no-store'
    assert account_client.patch('/editorial/research', headers={'Cookie': headers['Cookie']}, json={'enabled': False}).status_code == 403
    assert account_client.patch('/editorial/research', headers=headers, json={'enabled': False}).json() == {'enabled': False}


def test_calls_reserve_before_provider_and_fail_closed(monkeypatch):
    events = []
    def call(*args): events.append('provider'); raise writing.StopRun('provider_unavailable')
    monkeypatch.setattr(writing, 'call', call)
    async def reserve(cost): assert cost > 0; events.append('reserve')
    with pytest.raises(writing.StopRun):
        asyncio.run(writing.generate(ResearchSettings(), writing.Review, 'Review', {}, reserve))
    assert events == ['reserve', 'provider']


def test_output_usage_and_schema_are_enforced(monkeypatch):
    payload = writing.request_payload(ResearchSettings(), writing.Draft, 'Instructions', {})
    assert payload['store'] is False and 'tools' not in payload
    assert payload['text']['format']['strict'] is True
    schema = payload['text']['format']['schema']
    assert schema['additionalProperties'] is False
    assert set(schema['required']) == set(schema['properties'])
    async def reserve(cost): pass
    monkeypatch.setattr(writing, 'call', lambda *a: (review().model_dump_json(), {'input_tokens': 10, 'output_tokens': 99999}))
    with pytest.raises(writing.StopRun, match='usage_outside_budget_bound'):
        asyncio.run(writing.generate(ResearchSettings(), writing.Review, 'Check', {}, reserve))


def test_authorized_ceiling_and_underpriced_models():
    assert ResearchSettings(monthly_usd='10').monthly_usd == 10
    with pytest.raises(ValueError): ResearchSettings(monthly_usd='15.01')
    with pytest.raises(ValueError): ResearchSettings(model='gpt-5.4-mini')
    with pytest.raises(ValueError): ResearchSettings(input_per_million='0.01')
