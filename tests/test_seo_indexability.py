"""Read-only SSR contract against an explicit isolated loopback preview."""
import os
import re
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

import httpx
import pytest

from app.research.publication import Page

pytestmark = pytest.mark.skipif(os.environ.get('FOROIA_INDEXABILITY_PREVIEW') != '1', reason='Requires isolated Nuxt preview')
BASE = 'http://127.0.0.1:13009'
SLUGS = ['streaming-api-openai-python-comparar-opciones-practicas', 'resumir-pdf-ia-comprobar-citas',
         'extraer-texto-pdf-python', 'notebooklm-pdf-fuentes-citas', 'validar-json-ia-python',
         'validar-respuestas-ia-pydantic-esquema-limites', 'api-claude-python-primera-peticion']


@pytest.fixture(scope='module')
def site():
    assert urlsplit(BASE).hostname == '127.0.0.1'
    with httpx.Client(base_url=BASE, trust_env=False, follow_redirects=False, timeout=20) as client:
        yield client


@pytest.mark.parametrize('slug', SLUGS)
def test_article_ssr_identity_metadata_schema_and_visible_content(site, slug):
    response = site.get('/articulos/' + slug)
    assert response.status_code == 200
    data = site.get('/api/articles/' + slug).json()
    page = Page(response.text)
    assert page.canonical == [BASE + '/articulos/' + slug]
    assert page.h1.strip() == data['title']
    assert len(page.meta['description']) > 50
    assert 'noindex' not in page.meta.get('robots', '') + response.headers.get('x-robots-tag', '')
    assert page.meta['og:title'] == page.meta['twitter:title'] == data['title']
    assert page.meta['og:url'] == page.canonical[0]
    assert page.meta['twitter:card'] == 'summary_large_image'
    for h in re.findall(r'^##\s+(.+)$', data['body'], re.M):
        assert h in page.text
    schemas = [s for s in page.ld if 'BlogPosting' in s.get('@type', [])]
    assert len(schemas) == 1
    schema = schemas[0]
    assert schema['headline'] == data['title']
    assert schema['datePublished'] == data['published_at']
    assert schema['dateModified'] == data['updated_at']
    assert schema['citation'] == [s['url'] for s in data['sources']]
    assert schema['mainEntityOfPage'] == page.canonical[0]
    assert any(s.get('@type') == 'BreadcrumbList' for s in page.ld)


def test_sitemap_public_canonical_pages_and_private_exclusions(site):
    root = ET.fromstring(site.get('/sitemap.xml').text)
    assert root.tag.endswith('sitemapindex')
    urls = []
    for child in root.findall('.//{*}loc'):
        assert child.text.startswith(BASE + '/')
        response = site.get(child.text)
        assert response.status_code == 200
        urls += [e.text for e in ET.fromstring(response.text).findall('.//{*}loc')]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert not any(part in u for part in ['/blog/', '/editorial', '/cuenta', '/recursos/', '#'])
        response = site.get(u)
        page = Page(response.text)
        assert response.status_code == 200
        assert page.canonical == [u]
        assert 'noindex' not in page.meta.get('robots', '')
    assert all(BASE + '/articulos/' + s in urls for s in SLUGS)
    assert 'Allow: /' in site.get('/robots.txt').text
    assert BASE + '/sitemap.xml' in site.get('/robots.txt').text


@pytest.mark.parametrize('section', ['actualidad', 'herramientas', 'programacion', 'tutoriales'])
def test_legacy_redirect_keeps_section_and_pagination(site, section):
    response = site.get(f'/blog/{section}?pagina=2')
    assert response.status_code == 301
    assert response.headers['location'] == f'/{section}?pagina=2'


def test_pagination_downloads_and_true_404s(site):
    page = Page(site.get('/programacion').text)
    assert '/programacion?pagina=2' in page.links
    second = site.get('/programacion?pagina=2')
    assert second.status_code == 200
    assert Page(second.text).canonical == [BASE + '/programacion?pagina=2']
    assert site.get('/articulos/does-not-exist-test').status_code == 404
    assert site.get('/does-not-exist-test').status_code == 404
    assert site.get('/programacion?pagina=999').status_code == 404
    for filename in ['streaming_texto.py', 'primera_peticion_claude.py']:
        r = site.get('/recursos/api-ia/' + filename)
        assert r.status_code == 200 and '__main__' in r.text


def test_private_and_intentionally_empty_routes_remain_noindex(site):
    for path in ['/editorial', '/editorial/investigacion', '/moderacion']:
        r = site.get(path)
        assert r.status_code == 302 and r.headers['location'] == '/cuenta'
        assert 'noindex' in r.headers['x-robots-tag']
    assert 'noindex' in site.get('/cuenta').headers['x-robots-tag']
    for path in ['/foro', '/informacion/aviso-legal', '/informacion/privacidad']:
        assert 'noindex' in Page(site.get(path).text).meta['robots']
