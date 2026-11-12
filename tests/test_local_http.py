"""Pruebas HTTP optativas contra los servicios locales ya arrancados."""
import base64
import json
import os
import uuid
from functools import lru_cache
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get('FOROIA_LOCAL_HTTP') != '1',
    reason='Requiere servicios locales y FOROIA_LOCAL_HTTP=1',
)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def request(port, path, method='GET', headers=None, body=None):
    opener = build_opener(ProxyHandler({}), NoRedirect())
    data = json.dumps(body).encode() if body is not None else None
    try:
        response = opener.open(
            Request(f'http://127.0.0.1:{port}{path}', method=method,
                    headers=headers or {}, data=data), timeout=15
        )
    except HTTPError as error:
        response = error
    with response:
        return response.code, response.read().decode('utf-8')


@lru_cache
def editorial_session():
    env = {}
    for line in (Path(__file__).resolve().parents[1] / '.env').read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            env[key.strip()] = value.strip()
    if not env.get('EDITORIAL_PASSWORD'):
        pytest.skip('Panel editorial no configurado en .env')
    payload = json.dumps({'email': env.get('BOOTSTRAP_EMAIL', 'editor@localhost.test'), 'password': env['EDITORIAL_PASSWORD']}).encode()
    with build_opener(ProxyHandler({})).open(Request('http://127.0.0.1:3000/api/community/auth/login', data=payload,
            headers={'Origin': 'http://127.0.0.1:3000', 'Content-Type': 'application/json'}), timeout=15) as response:
        cookies = SimpleCookie()
        for line in response.headers.get_all('Set-Cookie', []):
            cookies.load(line)
    return {'Cookie': '; '.join(f'{k}={v.value}' for k,v in cookies.items())}, cookies['foroia_csrf'].value


def editorial_headers(mutation=False):
    headers, csrf = editorial_session()
    headers = headers.copy()
    if mutation:
        headers |= {'Origin': 'http://127.0.0.1:3000', 'Content-Type': 'application/json', 'X-CSRF-Token': csrf}
    return headers


@pytest.mark.parametrize('port,path,status', [
    (8000, '/articles', 200),
    (8000, '/sections', 200),
    (8000, '/articles/no-existe-prueba-local', 404),
    (8000, '/articles?limit=51', 422),
    (8000, '/editorial/articles', 401),
    (3000, '/api/articles', 200),
    (3000, '/api/sections', 200),
    (3000, '/blog/actualidad', 200),
    (3000, '/blog/inventada', 404),
    (3000, '/blog/actualidad?pagina=1', 404),
    (3000, '/articulos/no-existe-prueba-local', 404),
    (3000, '/editorial', 302),
    (3000, '/api/editorial/articles', 401),
    (3000, '/api/articles-sitemap', 404),
])
def test_blog_routes(port, path, status):
    assert request(port, path)[0] == status


def test_editorial_csrf_and_flow():
    h = editorial_headers()
    assert request(3000, '/api/editorial/articles', headers=h)[0] == 200
    # Sin Origin del propio sitio se rechaza la mutación.
    assert request(3000, '/api/editorial/articles', 'POST', headers=h | {'Content-Type': 'application/json'}, body={})[0] == 403
    assert request(3000, '/api/editorial/articles', 'POST', headers=h | {'Content-Type': 'application/json', 'Origin': 'https://evil.example'}, body={})[0] == 403

    m = editorial_headers(mutation=True)
    slug = f'prueba-local-{uuid.uuid4().hex[:10]}'
    article = {
        'slug': slug, 'title': 'Prueba local del flujo editorial', 'section': 'tutoriales', 'author_name': 'Prueba automatizada',
        'summary': 'Artículo temporal creado por la prueba local; se archiva al terminar la verificación.',
        'body': '## Prueba\n\nTexto de prueba <script>alert(1)</script>.\n\n' + 'Contenido. ' * 40,
        'sources': [{'title': 'Ejemplo', 'url': 'https://example.com/', 'language': 'en'}],
    }
    status, body = request(3000, '/api/editorial/articles', 'POST', headers=m, body=article)
    assert status == 201, body
    aid = json.loads(body)['id']
    try:
        assert request(3000, f'/articulos/{slug}')[0] == 404
        assert request(3000, f'/api/editorial/articles/{aid}/status', 'POST', headers=m, body={'status': 'review'})[0] == 200
        assert request(3000, f'/api/editorial/articles/{aid}/status', 'POST', headers=m, body={'status': 'published'})[0] == 200
        status, html = request(3000, f'/articulos/{slug}')
        assert status == 200
        assert '<script>alert(1)</script>' not in html
        assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html
        assert f'http://localhost:3000/articulos/{slug}' in html and 'BlogPosting' in html
        assert 'Fuentes originales' in html
        assert slug in request(3000, '/sitemap.xml')[1]
        assert slug in request(3000, '/')[1]
        assert slug in request(3000, '/blog/tutoriales')[1]
    finally:
        request(3000, f'/api/editorial/articles/{aid}/status', 'POST', headers=m, body={'status': 'archived'})
    assert request(8000, f'/articles/{slug}')[0] == 404
    assert request(3000, f'/articulos/{slug}')[0] == 404
    for path in ['/', '/blog/tutoriales', '/sitemap.xml', '/api/articles']:
        assert slug not in request(3000, path)[1]


@pytest.mark.parametrize('port,path,method,status', [
    (8000, '/health', 'GET', 200),
    (8000, '/topics', 'GET', 200),
    (8000, '/topics/no-existe-prueba-local', 'GET', 404),
    (8000, '/categories/herramientas-ia/topics?limit=51', 'GET', 422),
    (3000, '/categoria/herramientas-ia', 'GET', 200),
    (3000, '/categoria/no-existe-prueba-local', 'GET', 404),
    (3000, '/tema/no-existe-prueba-local', 'GET', 404),
    (3000, '/api/categories/herramientas-ia/topics', 'GET', 200),
    (3000, '/api/topics/no-existe-prueba-local', 'GET', 404),
    (3000, '/api/topics?limit=0', 'GET', 422),
    (3000, '/api/categories', 'POST', 405),
    (3000, '/api/health', 'GET', 404),
    (3000, '/sitemap.xml', 'GET', 200),
    (3000, '/robots.txt', 'GET', 200),
])
def test_public_routes(port, path, method, status):
    assert request(port, path, method)[0] == status


def test_categories_proxy_and_ssr():
    api_status, api_body = request(8000, '/categories')
    proxy_status, proxy_body = request(3000, '/api/categories')
    assert api_status == proxy_status == 200
    categories = json.loads(api_body)
    assert json.loads(proxy_body) == categories
    assert any(category['name'] == 'Programación e IA' for category in categories)
    status, html = request(3000, '/')
    assert status == 200
    assert 'rel="canonical"' in html
    assert 'http://localhost:3000/' in html
    for category in categories:
        assert category['name'] in html


def test_information_and_empty_forum_categories():
    for slug in ['contacto', 'criterio-editorial', 'normas', 'cookies', 'privacidad', 'aviso-legal']:
        status, html = request(3000, '/informacion/' + slug)
        assert status == 200 and 'admin@foroiaaldia.com' in html
        assert f'http://localhost:3000/informacion/{slug}' in html
    assert request(3000, '/informacion/does-not-exist')[0] == 404
    assert request(3000, '/informacion/constructor')[0] == 404
    categories = json.loads(request(8000, '/categories')[1])
    sitemap = request(3000, '/sitemap.xml')[1]
    for category in categories:
        if category['published_topics'] == 0:
            html = request(3000, '/categoria/' + category['slug'])[1]
            assert 'noindex, follow' in html
            assert f'/categoria/{category["slug"]}</loc>' not in sitemap
