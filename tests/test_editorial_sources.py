from datetime import UTC,datetime
import asyncio
import pytest

from app.research import sources


def test_document_sections_are_substantial_and_focus_preserves_provenance():
    from app.research.documents import document_sections
    from app.research.queue import focused_document
    from app.research.writing import StopRun
    raw=('<main><h2 id="validation">Strict validation</h2><p>'+('Validate the input before processing. '*40)+'</p><h2>Navigation</h2><p>Links</p></main>').encode()
    sections=document_sections(raw)
    assert len(sections)==1 and sections[0]['anchor']=='validation'
    doc={'url':'https://docs.python.org/3.12/library/json.html','title':'JSON','text':'whole document','sections':sections,'organization':'python'}
    focused=focused_document(doc,sections[0]['key'])
    assert focused['url'].endswith('#validation') and focused['raw_document_url']==doc['url']
    assert focused['text']==sections[0]['text'] and 'sections' not in focused
    assert focused_document(doc,sections[0]['key'])['id']==focused['id']
    with pytest.raises(StopRun):focused_document(doc,'missing')


def test_markdown_document_sections_keep_real_text():
    from app.research.documents import document_sections
    raw=('## Reliable outputs\n'+('Check the returned structure and handle invalid input. '*25)+'\n## Links\nShort').encode()
    sections=document_sections(raw)
    assert len(sections)==1 and sections[0]['title']=='Reliable outputs' and sections[0]['anchor'] is None


def test_news_index_never_trusts_a_missing_date_or_foreign_link():
    feed=next(f for f in sources.FEEDS if f.host=='www.anthropic.com')
    html=b'<a href="/news/example-release">New research announcement</a><a href="http://127.0.0.1/private">Private</a><a href="https://evil.test/news/a">Foreign</a>'
    rows=sources.parse_news_index(html,feed)
    assert len(rows)==1 and rows[0]['published'] is None and rows[0]['url']=='https://www.anthropic.com/news/example-release'
    assert sources.article_date(b'<article>No date supplied</article>') is None
    assert sources.article_date(b'<script type="application/ld+json">{"datePublished":"2026-10-24T10:00:00Z"}</script>')==datetime(2026,10,24,10,tzinfo=UTC)


def test_corporate_parent_and_scientific_host_are_not_independent_authorship():
    assert sources.source_attribution('https://deepmind.google/blog/example',b'','google')['organization']=='google'
    assert sources.source_attribution('https://www.anthropic.com/news/example',b'','anthropic')['organization_verified']
    paper=sources.source_attribution('https://arxiv.org/abs/1234.5678',b'','unverified_scientific_authors')
    assert paper['organization_verified'] is False


def test_html_news_without_verified_date_is_excluded_before_generation(monkeypatch):
    html_feed=next(f for f in sources.FEEDS if f.host=='www.anthropic.com')
    monkeypatch.setattr(sources,'FEEDS',(html_feed,))
    def fetch(url,max_bytes=sources.MAX_BYTES):
        if url==html_feed.url:return url,b'<a href="/news/example-release">New AI model release</a>'
        return url,b'<article>'+b'An announcement without a verifiable timestamp. '*25+b'</article>'
    monkeypatch.setattr(sources,'fetch',fetch)
    docs,stats=asyncio.run(sources.collect(datetime(2026,10,24,12,tzinfo=UTC),set()))
    assert docs==[] and stats['fetch_errors'][0]['code']=='unverified_or_stale_date'
