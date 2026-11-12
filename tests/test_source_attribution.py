import asyncio
from datetime import UTC, datetime
from html import escape
import json

import pytest

from app.research import sources
from app.research import writing


def byline(namespace, identifier, staff=False):
    raw = json.dumps({'authors': [{'author': {'isHf': staff}, 'org': {'name': namespace, '_id': identifier, 'type': 'org'}}]})
    return ('<div data-target="BlogAuthorsByline" data-props="' + escape(raw, quote=True) + '"></div>').encode()


@pytest.mark.parametrize('namespace', ['microsoft', 'allenai'])
def test_curated_namespace_requires_matching_byline(namespace):
    organization, identifier = sources.HF_ORGANIZATIONS[namespace]
    url = f'https://huggingface.co/blog/{namespace}/example'
    result = sources.source_attribution(url, byline(namespace, identifier), 'huggingface')
    assert result['organization'] == organization and result['organization_verified'] is True
    for invalid in [b'', b'<div data-target="BlogAuthorsByline" data-props></div>',
                    b'<div data-target="BlogAuthorsByline" data-props="[]"></div>', byline(namespace, 'incorrect')]:
        assert sources.source_attribution(url, invalid, 'huggingface')['organization_verified'] is False


def test_unregistered_namespace_does_not_prove_independence():
    data = byline('ibm-research', 'unverified-id')
    result = sources.source_attribution('https://huggingface.co/blog/ibm-research/example', data, 'huggingface')
    assert result['organization'] == 'huggingface' and result['organization_verified'] is False
    official = sources.source_attribution('https://huggingface.co/blog/example', byline('', '', staff=True), 'huggingface')
    assert official['organization_verified'] is True
    assert sources.independent_organizations([result, official]) == {'huggingface'}


def test_independence_ignores_unconfirmed_groups_and_preserves_old_expedients():
    evidence = [{'organization': 'microsoft', 'organization_verified': True},
                {'organization': 'huggingface', 'organization_verified': False}]
    assert sources.independent_organizations(evidence) == {'microsoft'}
    assert sources.independent_organizations([{'organization': 'openai'}, {'organization': 'google'}]) == {'openai', 'google'}


def test_collection_tries_bounded_additional_candidates_and_redacts_errors(monkeypatch):
    now = datetime(2026, 10, 24, 1, tzinfo=UTC)
    xml = ('<rss><channel>' + ''.join(
        f'<item><title>AI model</title><link>https://openai.com/news/test-{i}</link><pubDate>Sat, 24 Oct 2026 00:00:00 GMT</pubDate></item>'
        for i in range(14)) + '</channel></rss>').encode()
    attempted = []
    def fetch(url, max_bytes=sources.MAX_BYTES):
        if url == sources.FEEDS[0].url:
            return url, xml
        if url in {f.url for f in sources.FEEDS}:
            return url, b'<rss><channel/></rss>'
        attempted.append(url)
        if len(attempted) <= 8:
            raise sources.SourceError('sensitive response body should never enter report', 'http_status', 403)
        return url, b'<p>' + b'Research context. ' * 100 + b'</p>'
    monkeypatch.setattr(sources, 'fetch', fetch)
    evidence, report = asyncio.run(sources.collect(now, set()))
    assert len(attempted) == 12 and len(evidence) == 4
    assert report['fetch_failures'] == 8 and len(report['fetch_errors']) == 8
    assert report['fetch_errors'][0]['http_status'] == 403
    assert 'sensitive response' not in json.dumps(report)
    assert report['source_organizations'] == ['openai']


def test_collection_keeps_maximum_eight_sources(monkeypatch):
    now = datetime(2026, 10, 24, 1, tzinfo=UTC)
    xml = ('<rss><channel>' + ''.join(
        f'<item><title>AI</title><link>https://openai.com/news/{i}</link><pubDate>Sat, 24 Oct 2026 00:00:00 GMT</pubDate></item>'
        for i in range(14)) + '</channel></rss>').encode()
    calls = []
    def fetch(url, max_bytes=sources.MAX_BYTES):
        if url in {f.url for f in sources.FEEDS}:
            return url, xml if url == sources.FEEDS[0].url else b'<rss/>'
        calls.append(url)
        return url, b'<p>' + b'Original source context. ' * 100 + b'</p>'
    monkeypatch.setattr(sources, 'fetch', fetch)
    evidence, _ = asyncio.run(sources.collect(now, set()))
    assert len(evidence) == len(calls) == 8


def test_article_cannot_count_unverified_organization_as_corroboration():
    from test_research import draft, EVIDENCE
    evidence = [{**item, 'organization_verified': item['organization'] == 'openai'} for item in EVIDENCE]
    with pytest.raises(writing.StopRun, match='insufficient_independent_sources'):
        writing.validate_draft(draft(), evidence, [])


def test_resumed_review_rechecks_new_attribution_metadata(monkeypatch):
    now = datetime(2026, 10, 24, 1, tzinfo=UTC)
    metadata = [{'id': i, 'url': f'https://huggingface.co/blog/{namespace}/example',
                 'organization': sources.HF_ORGANIZATIONS[namespace][0], 'organization_verified': True,
                 'published': now.isoformat()} for i, namespace in enumerate(['microsoft', 'allenai'], 1)]
    monkeypatch.setattr(sources, 'fetch', lambda url: (url, byline('microsoft', 'changed-id')))
    with pytest.raises(sources.SourceError, match='autoría'):
        asyncio.run(sources.restore(metadata, now))
