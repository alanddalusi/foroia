"""Opt-in against an isolated loopback deployment, never the production site."""
import os
import re
import uuid
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import pytest

pytestmark = pytest.mark.skipif(os.environ.get('FOROIA_SEO_REVIEW') != '1', reason='Requires isolated review deployment')
BASE = 'http://localhost:13001'


@pytest.fixture(scope='module')
def review():
    import httpx
    assert urlparse(BASE).hostname == 'localhost'
    client = httpx.Client(base_url=BASE, trust_env=False, timeout=30)
    r = client.post('/api/community/auth/login', headers={'Origin': BASE}, json={
        'email': 'reviewer@example.test', 'password': os.environ['FOROIA_REVIEW_PASSWORD']})
    assert r.status_code == 200
    headers = {'Origin': BASE, 'X-CSRF-Token': client.cookies['foroia_csrf']}
    ids = []
    slugs = []
    try:
        for i in range(13):
            slug = f'prueba-seo-aislada-{uuid.uuid4().hex[:10]}'
            r = client.post('/api/editorial/articles', headers=headers, json={
                'slug': slug, 'title': f'Prueba aislada SEO número {i}', 'section': 'actualidad',
                'summary': 'Contenido de prueba únicamente para la validación aislada de metadatos y navegación.',
                'body': 'Texto de prueba aislado, no es una noticia ni una recomendación. ' * 10,
                'author_name': 'Prueba automatizada aislada',
                'sources': [{'title': 'Fuente de prueba', 'url': 'https://example.test/', 'language': 'es'}]})
            assert r.status_code == 201
            aid = r.json()['id']; ids.append(aid); slugs.append(slug)
            for state in ['review', 'published']:
                assert client.post(f'/api/editorial/articles/{aid}/status', headers=headers, json={'status': state}).status_code == 200
        yield client, slugs
    finally:
        for aid in ids:
            client.post(f'/api/editorial/articles/{aid}/status', headers=headers, json={'status': 'archived'})
        client.close()


def test_ssr_redirects_pagination_and_sitemaps(review):
    import httpx
    _, slugs = review
    c = httpx.Client(base_url=BASE, trust_env=False)
    r = c.get('/blog/actualidad?pagina=2')
    assert r.status_code == 301 and r.headers['location'] == '/actualidad?pagina=2'
    first, second = c.get('/actualidad'), c.get('/actualidad?pagina=2')
    assert first.status_code == second.status_code == 200
    assert len(re.findall('class="article-card', first.text)) == 12
    assert '?pagina=2' in first.text and 'rel="next"' in first.text
    assert f'{BASE}/actualidad?pagina=2' in second.text
    assert c.get('/actualidad?pagina=99').status_code == 404
    assert c.get('/inventada').status_code == 404
    assert 'noindex' in c.get('/tutoriales').text
    assert 'noindex' in c.get('/foro').text
    html = c.get('/articulos/' + slugs[0]).text
    assert 'Texto de prueba aislado' in html and 'BlogPosting' in html and 'BreadcrumbList' in html
    assert 'Organization' in html or 'Person' in html
    assert '/images/actualidad.png' in html and 'width="1200"' in html
    assert c.get('/images/actualidad.png').headers['content-type'].startswith('image/png')
    root = ET.fromstring(c.get('/sitemap.xml').text)
    assert root.tag.endswith('sitemapindex')
    urls = []
    for node in root.findall('.//{*}loc'):
        response = c.get(node.text)
        assert response.status_code == 200, node.text
        urls.extend(e.text for e in ET.fromstring(response.text).findall('.//{*}loc'))
    assert all(BASE + '/articulos/' + slug in urls for slug in slugs)
    assert BASE + '/tutoriales' not in urls and BASE + '/foro' not in urls
    assert all('/blog/' not in u and '#' not in u for u in urls)
    assert c.get('/sitemaps/articles/999').status_code == 404
    assert c.get('/ads.txt').status_code == 404
    assert c.get('/api/seo/inventory').status_code == 404
    assert c.get('/api/editorial/analytics').status_code == 401
    assert 'google-site-verification' in c.get('/').text
    c.close()


def test_consent_and_mobile(review):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={'width':390,'height':844})
        calls = []
        context.route('https://www.googletagmanager.com/**', lambda route: (calls.append(route.request.url), route.fulfill(status=200, body='')))
        context.route('https://*.google-analytics.com/**', lambda route: route.abort())
        page = context.new_page(); errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(BASE, wait_until='networkidle')
        assert calls == []
        assert page.get_by_role('heading', name='Analítica opcional').is_visible()
        page.get_by_role('button', name='Rechazar analítica').click()
        page.reload(wait_until='networkidle'); assert calls == []
        page.get_by_role('button', name='Preferencias de analítica').click()
        page.get_by_role('button', name='Aceptar analítica').click()
        page.wait_for_timeout(300)
        assert len(calls) == 1
        page.goto(BASE + '/actualidad?private=not-sent', wait_until='networkidle')
        location = page.evaluate("window.dataLayer.filter(x=>x[0]==='event').at(-1)[2].page_location")
        assert location == BASE + '/actualidad'
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert page.locator('.site-header').bounding_box()['height'] < 240
        page.keyboard.press('Tab')
        assert page.evaluate("document.activeElement.tagName !== 'BODY'")
        page.get_by_role('button', name='Preferencias de analítica').click()
        page.get_by_role('button', name='Rechazar analítica').click()
        page.wait_for_load_state('networkidle')
        assert len(calls) == 2  # one load on accept, one after full navigation
        assert not errors
        context.close(); browser.close()
