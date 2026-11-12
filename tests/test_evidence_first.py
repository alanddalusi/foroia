"""Offline regressions and end-to-end publication in the disposable test DB only."""
import asyncio
import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from test_research import EVIDENCE, Redis, client, database, draft, review
from app.models import Article, ResearchControl, ResearchRun
from app.research import evidence, sources, worker, writing
from app.research.config import ResearchSettings


def grounded(sources):
    payload = draft().model_dump()
    refs = []
    for i, paragraph in enumerate(payload['paragraphs']):
        fid = sources[i % 2]['fragments'][0]['fragment_id']
        paragraph['evidence'] = [{'fragment_id': fid}]
        refs.append({'fragment_id': fid})
    payload.update(title_evidence=refs[:1], summary_evidence=refs[:1])
    return writing.GroundedDraft.model_validate(payload)


def approved_payload(payload):
    data = json.loads(payload['input'])
    by_pair = {(s['id'], f['text']): f['fragment_id'] for s in data['sources'] for f in s['fragments']}
    proposal = data['draft']
    checks = []
    for target in data['targets']:
        paragraph = proposal['paragraphs'][0]
        if target['target_id'].startswith('p'):
            paragraph = proposal['paragraphs'][int(target['target_id'].split('.')[0][1:]) - 1]
        refs = [by_pair[(r['source_id'], r['quote'])] for r in paragraph['evidence']]
        checks.append({'target_id': target['target_id'], 'supported': True, 'fragment_ids': refs})
    return dict(review().model_dump(), checks=checks)


def test_ids_are_order_independent_and_content_versioned():
    one = evidence.catalogue(EVIDENCE)
    reverse = evidence.catalogue(list(reversed(EVIDENCE)))
    assert one[0]['source_key'] == reverse[1]['source_key']
    assert one[0]['fragments'] == reverse[1]['fragments']
    changed = evidence.catalogue([dict(EVIDENCE[0], text='Changed text. ' + EVIDENCE[0]['text'])])[0]
    assert changed['source_key'] == one[0]['source_key']
    assert changed['content_sha256'] != one[0]['content_sha256']
    assert changed['fragments'][0]['fragment_id'] != one[0]['fragments'][0]['fragment_id']
    assert all(s['url'] and s['title'] and s['published'] and s['retrieved_at'] for s in one)
    evidence.index(one)


def test_context_is_balanced_bounded_and_keeps_original_snapshot():
    corpus = [dict(EVIDENCE[i % 2], id=i, url=f'https://openai.com/news/source-{i}',
        text=('Una evidencia pública y verificable. ' * 700)) for i in range(8)]
    catalogue = evidence.catalogue(corpus)
    payload = evidence.model_sources(catalogue)
    assert len(payload) == 8
    assert sum(len(f['text'].encode()) for s in payload for f in s['fragments']) <= 24000
    assert all(len(s['text']) == 18000 for s in catalogue)
    assert all(s['fragments'] for s in payload)


def test_unbacked_headline_numbers_are_not_exempt():
    proposal = draft()
    proposal.title += ' con 987 mejoras'
    with pytest.raises(writing.StopRun, match='unsupported_number'):
        writing.validate_draft(proposal, EVIDENCE, [])


def test_stable_internal_ids_do_not_leak_into_visible_citation_numbers():
    corpus = [dict(s, id=100_000_000_000 + i) for i, s in enumerate(EVIDENCE)]
    catalogue = evidence.catalogue(corpus)
    article = writing.validate_draft(writing.resolve_grounded(grounded(catalogue), catalogue), catalogue, [])
    assert '[1]' in article.body and '[2]' in article.body
    assert '100000000000' not in article.body
    assert article.sources[0].title.startswith('[1]')


def test_valid_but_insufficient_catalogue_never_calls_provider(client):
    async def operation(db):
        db.add(ResearchControl(id=1, enabled=True))
        row = ResearchRun(editorial_date=datetime(2026, 10, 24).date())
        db.add(row); await db.commit()
        redis = Redis(); redis.value = b'owner'
        async def collect(now, urls): return [EVIDENCE[0]], {}
        async def provider(*args): pytest.fail('Provider must not run without sufficient evidence')
        with pytest.raises(writing.StopRun, match='insufficient_sources'):
            await worker.pipeline(db, row, ResearchSettings(), redis, b'owner', collect, provider)
        assert row.reserved_microusd == 0 and row.article_id is None
    database(operation)


def test_real_punctuation_regression_uses_exact_server_text():
    fixture = json.loads((Path(__file__).parent / 'fixtures/research_evidence_spacing.json').read_text())
    corpus = [dict(s, text=fixture['extracted_text'] + ' Additional context.' * 30) for s in EVIDENCE]
    broken = draft()
    broken.paragraphs[0].evidence[0].quote = fixture['model_quote']
    with pytest.raises(writing.StopRun, match='invalid_evidence') as caught:
        writing.validate_draft(broken, corpus, [])
    assert caught.value.details == [{'paragraph': 1, 'source_id': 1, 'code': 'quote_not_in_source', 'quote': fixture['model_quote']}]
    catalogue = evidence.catalogue(corpus)
    resolved = writing.resolve_grounded(grounded(catalogue), catalogue)
    assert 'highlighting ,' in resolved.paragraphs[0].evidence[0].quote
    assert writing.validate_draft(resolved, catalogue, []).sources


@pytest.mark.parametrize('mode', ['unknown', 'tampered', 'metadata'])
def test_unknown_ids_tampering_and_unattributed_metadata_fail(mode):
    catalogue = evidence.catalogue(EVIDENCE)
    proposal = grounded(catalogue)
    if mode == 'unknown': proposal.paragraphs[0].evidence[0].fragment_id = 'e_' + '0' * 32
    if mode == 'tampered': catalogue[0]['fragments'][0]['text'] += ' invented'
    if mode == 'metadata':
        extra=evidence.catalogue([dict(EVIDENCE[0],id=999,url='https://openai.com/index/unattributed-fixture')])[0]
        catalogue.append(extra)
        proposal.title_evidence[0].fragment_id=extra['fragments'][0]['fragment_id']
    with pytest.raises((writing.StopRun, ValueError)):
        writing.resolve_grounded(proposal, catalogue)


def test_real_generate_adapter_never_asks_model_to_copy_quotes(monkeypatch):
    catalogue = evidence.catalogue(EVIDENCE)
    def provider(config, payload):
        assert payload['text']['format']['name'] == 'groundeddraft'
        schema = json.dumps(payload['text']['format']['schema'])
        assert 'quote' not in schema and 'source_id' not in schema
        assert 'NO traduzcas' not in payload['instructions']
        assert all('text' not in s for s in json.loads(payload['input'])['sources'])
        return grounded(catalogue).model_dump_json(), {'input_tokens': 10, 'output_tokens': 100}
    monkeypatch.setattr(writing, 'call', provider)
    events = []
    async def reserve(cost): events.append(cost)
    result = asyncio.run(writing.generate(ResearchSettings(), writing.Draft, writing.VOICE, {'sources': catalogue}, reserve))
    assert isinstance(result, writing.Draft) and len(events) == 1
    writing.validate_draft(result, catalogue, [])


@pytest.mark.parametrize('mode', ['valid', 'missing', 'duplicate', 'unsupported', 'foreign_id', 'uncited'])
def test_claim_coverage_and_evidence_membership_are_required(monkeypatch, mode):
    catalogue = evidence.catalogue(EVIDENCE)
    proposal = writing.resolve_grounded(grounded(catalogue), catalogue)
    def provider(config, payload):
        value = approved_payload(payload)
        if mode == 'missing': value['checks'].pop()
        if mode == 'duplicate': value['checks'][-1] = value['checks'][0]
        if mode == 'unsupported': value['checks'][0]['supported'] = False
        if mode == 'foreign_id': value['checks'][0]['fragment_ids'] = ['e_' + '0' * 32]
        if mode == 'uncited': value['checks'][-1]['fragment_ids'] = [catalogue[0]['fragments'][-1]['fragment_id']]
        return json.dumps(value), {'input_tokens': 10, 'output_tokens': 100}
    monkeypatch.setattr(writing, 'call', provider)
    async def reserve(cost): pass
    result = asyncio.run(writing.generate(ResearchSettings(), writing.Review, writing.REVIEW_INSTRUCTIONS,
        {'sources': catalogue, 'draft': proposal.model_dump()}, reserve))
    assert result.approved is (mode in {'valid','uncited'})
    assert result.supported is (mode in {'valid','uncited'})


@pytest.mark.parametrize('mode', ['publish', 'correct', 'reject'])
def test_complete_pipeline_with_real_adapter_and_no_paid_calls(client, monkeypatch, mode):
    catalogue = evidence.catalogue(EVIDENCE)
    calls = []
    def provider(config, payload):
        kind = payload['text']['format']['name']; calls.append(kind)
        if kind == 'groundeddraft':
            value = grounded(catalogue).model_dump()
            if mode == 'correct' and calls.count(kind) > 1:
                value['paragraphs'][0]['text'] = value['paragraphs'][0]['text'].replace('El anuncio abre', 'La documentación abre')
        else:
            value = approved_payload(payload)
            if mode == 'reject' or (mode == 'correct' and calls.count(kind) == 1):
                value['checks'][0]['supported'] = False
        return json.dumps(value), {'input_tokens': 10, 'output_tokens': 100}
    monkeypatch.setattr(writing, 'call', provider)
    async def operation(db):
        db.add(ResearchControl(id=1, enabled=True))
        row = ResearchRun(editorial_date=datetime(2026, 10, 24).date())
        db.add(row); await db.commit()
        redis = Redis(); redis.value = b'owner'
        async def collect(now, urls): return copy.deepcopy(EVIDENCE), {'candidate_count': 2}
        if mode == 'reject':
            with pytest.raises(writing.StopRun, match='review_rejected'):
                await worker.pipeline(db, row, ResearchSettings(), redis, b'owner', collect, writing.generate)
        else:
            await worker.pipeline(db, row, ResearchSettings(), redis, b'owner', collect, writing.generate)
        article = await db.get(Article, row.article_id)
        assert article.status == ('draft' if mode == 'reject' else 'published')
        assert row.reserved_microusd <= 150000
        assert {s['text'] for s in row.report['evidence_catalogue']} == {s['text'] for s in EVIDENCE}
        assert row.report['versions'][-1]['review']['checks']
        assert len(calls) == {'publish':2,'correct':4,'reject':3}[mode]
    database(operation)
    response = client.get('/articles')
    assert len(response.json()['items']) == (0 if mode == 'reject' else 1)


@pytest.mark.parametrize('full', [True, False])
def test_403_falls_back_only_to_explicit_full_rss_without_retry(monkeypatch, full):
    content = '<content:encoded><![CDATA[<p>' + 'Official documentation for a released model. ' * 30 + '</p>]]></content:encoded>' if full else '<description>Short announcement only</description>'
    xml = ('<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item>'
        '<title>New AI model</title><link>https://openai.com/news/example</link>'
        '<pubDate>Sat, 24 Oct 2026 00:00:00 GMT</pubDate>' + content + '</item></channel></rss>').encode()
    urls = []
    def fetch(url, max_bytes=sources.MAX_BYTES):
        urls.append(url)
        if url in {f.url for f in sources.FEEDS}:
            return url, xml if url == sources.FEEDS[0].url else b'<rss/>'
        raise sources.SourceError('blocked', 'http_status', 403)
    monkeypatch.setattr(sources, 'fetch', fetch)
    rows, stats = asyncio.run(sources.collect(datetime(2026, 10, 24, 12, tzinfo=UTC), set()))
    assert len(rows) == (1 if full else 0)
    assert urls.count('https://openai.com/news/example') == 1
    assert stats['fetch_errors'][0]['http_status'] == 403
    if full:
        assert rows[0]['retrieval_method'] == 'rss_full_content'
        assert rows[0]['organization_verified'] is True


def test_metadata_may_use_another_verified_fragment_of_an_attributed_source():
    catalogue=evidence.catalogue(EVIDENCE)
    proposal=grounded(catalogue)
    proposal.title_evidence[0].fragment_id=catalogue[0]['fragments'][-1]['fragment_id']
    resolved=writing.resolve_grounded(proposal,catalogue)
    assert resolved.title==proposal.title
    assert resolved.paragraphs[0].evidence[0].source_id==catalogue[0]['id']


@pytest.mark.parametrize('number,support,expected',[
    ('11.900','11,900 customers',True),('16,3','16.3 billion',True),
    ('11.900','11900 customers',True),('119','11900 customers',False),
    ('11','11900 customers',False),('1,2','12 billion',False),
    ('50,1','50.1 percent',True),('2026','2025 annual report',False)])
def test_numeric_evidence_preserves_magnitude_across_languages(number,support,expected):
    assert writing.supported_number(number,support) is expected


def test_complete_summary_removes_only_unfinished_trailing_sentence():
    from app.research.quality import complete_summary
    sentence='La noticia recoge un anuncio documentado y explica su alcance para los lectores.'
    assert complete_summary(sentence+' La fuente aporta cifras sobre ingresos, ')==sentence
    assert complete_summary(sentence)==sentence
    assert complete_summary('La cifra es 16.3 millones y no hay una frase completa')=='La cifra es 16.3 millones y no hay una frase completa'
