"""Local Nuxt build + read-only API stub. Google requests intercepted, no property used."""
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
from urllib.parse import urlsplit, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

pytestmark = pytest.mark.skipif(os.environ.get('FOROIA_ANALYTICS_LOCAL') != '1', reason='Requires local Nuxt build and Chromium')
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def site():
    import httpx
    class API(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            path = self.path.split('?')[0]
            data = {'/sections': [], '/categories': [], '/articles': {'items': [], 'page': 1, 'has_next': False}}
            articles = json.loads((ROOT/'editorial/phase1/publication.json').read_text(encoding='utf-8'))
            data['/sections'] = [{'slug': a['section'], 'name': a['section'].capitalize(), 'description': 'Guías y ejemplos de ' + a['section']} for a in articles]
            query = parse_qs(urlsplit(self.path).query)
            data['/articles'] = {'items': [a for a in articles if not query.get('section') or a['section'] == query['section'][0]], 'page': 1, 'has_next': False}
            data['/seo/inventory'] = {'articles': 3, 'topics': 0, 'sections': [a['section'] for a in articles]}
            data['/seo/entries'] = [dict(slug=a['slug'], updated_at='2026-10-23T12:00:00Z') for a in articles]
            for article in articles:
                article['published_at'] = '2026-10-23T12:00:00.123456Z'
                data['/articles/' + article['slug']] = {**article,
                    'updated_at': '2026-10-23T12:00:00.123456Z', 'reviewed_at': '2026-10-23T12:00:00.123456Z',
                    'comments_enabled': False, 'related': []}
            status = 401 if path == '/auth/me' else 200
            if path == '/auth/me' and self.headers.get('cookie', '') == 'foroia_session=research-fixture':
                status = 200
                data[path] = {'id': 1, 'role': 'editor', 'verified': True, 'display_name': 'Local fixture'}
            if path == '/editorial/research':
                data[path] = {'enabled': True, 'configured': True, 'worker_alive': True, 'model': 'test-fixture',
                    'at': '22:30', 'timezone': 'Europe/Madrid', 'auto_publish': True, 'monthly_usd': '5',
                    'daily_usd': '0.15', 'reserved_usd': '0.157429', 'feeds': [],
                    'runs': [{'id': day, 'date': f'2026-10-{day}', 'status': 'skipped', 'reason': 'migrated_local_budget',
                        'finished_at': f'2026-10-{day}T20:00:00Z', 'article_id': None, 'reserved_usd': '0.01', 'report': {}} for day in [22, 21]]}
            if path.endswith('/comments'):
                data[path] = {'items': [], 'next_cursor': None}
            self.send_response(status); self.send_header('Content-Type', 'application/json'); self.end_headers()
            self.wfile.write(json.dumps(data.get(path, {})).encode())
    api = ThreadingHTTPServer(('127.0.0.1', 0), API)
    threading.Thread(target=api.serve_forever, daemon=True).start()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    env = {**os.environ, 'NITRO_HOST': '127.0.0.1', 'NITRO_PORT': str(port),
        'NUXT_API_BASE': f'http://127.0.0.1:{api.server_port}', 'NUXT_PUBLIC_SITE_URL': base,
        'NUXT_PUBLIC_GA4_ID': 'G-LOCALTEST1', 'NUXT_PUBLIC_ANALYTICS_ENABLED': 'true',
        'NUXT_PUBLIC_LEGAL_NAME': 'Local test fixture', 'NUXT_PUBLIC_LEGAL_ADDRESS': 'Local test fixture',
        'NUXT_PUBLIC_LEGAL_TAX_ID': 'TEST-ONLY', 'NUXT_PUBLIC_REGISTRATION_ENABLED': 'false',
        'NUXT_PUBLIC_ACCOUNT_EMAIL_ENABLED': 'false', 'NUXT_EDITORIAL_API_TOKEN': ''}
    log = (ROOT/'.local/editorial-analytics-server.log').open('w', encoding='utf-8')
    process = subprocess.Popen([os.environ['FOROIA_NODE_BINARY'], '.output/server/index.mjs'], cwd=ROOT/'web', env=env, stdout=log, stderr=log)
    try:
        for _ in range(100):
            try:
                if httpx.get(base, trust_env=False).status_code == 200: break
            except httpx.HTTPError: pass
            assert process.poll() is None, 'Local Nuxt exited'
            time.sleep(.2)
        else: raise RuntimeError('Local Nuxt did not start')
        yield base
    finally:
        process.terminate(); process.wait(timeout=15); log.close(); api.shutdown(); api.server_close()


def context_for(browser):
    context = browser.new_context(viewport={'width':390, 'height':844})
    calls = []
    context.route('https://www.googletagmanager.com/**', lambda r: (calls.append(r.request.url), r.fulfill(status=200, body='/* intercepted; no GA server */')))
    context.route('https://*.google-analytics.com/**', lambda r: r.abort())
    return context, calls


def config(page):
    return page.evaluate("Array.from(window.dataLayer || []).find(x=>x[0]==='config')?.[2]")


def views(page):
    return page.evaluate("Array.from(window.dataLayer || []).filter(x=>x[0]==='event'&&x[1]==='page_view').map(x=>x[2])")


def test_delayed_consent_source_spa_and_withdrawal(site):
    from playwright.sync_api import sync_playwright, expect
    with sync_playwright() as p:
        browser = p.chromium.launch(); context, calls = context_for(browser); page = context.new_page()
        errors = []; page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(site + '/?email=private#secret', referer='https://www.google.com/search?q=private', wait_until='networkidle')
        assert calls == [] and views(page) == []
        page.locator('nav[aria-label=Principal]').get_by_role('link', name='Actualidad', exact=True).click()
        expect(page).to_have_url(site + '/actualidad')
        assert calls == []
        page.get_by_role('button', name='Aceptar analítica').click()
        page.wait_for_function("(window.dataLayer||[]).some(x=>x[0]==='event')")
        assert config(page)['page_referrer'] == 'https://www.google.com/'
        assert views(page)[0]['page_location'] == site + '/actualidad'
        assert views(page)[0]['page_title'] == page.title()
        page.locator('nav[aria-label=Principal]').get_by_role('link', name='Herramientas', exact=True).click()
        try:
            page.wait_for_function("(window.dataLayer||[]).filter(x=>x[0]==='event').length>=2", timeout=5000)
        except Exception:
            pytest.fail(json.dumps({'url': page.url, 'views': views(page), 'errors': errors, 'title': page.title(), 'h1': page.locator('h1').all_text_contents(), 'choice': page.evaluate("localStorage.getItem('foroia-analytics-consent-v1')")}))
        assert len(views(page)) == 2
        assert len(calls) == 1
        assert views(page)[1]['page_referrer'] == site + '/actualidad'
        assert views(page)[1]['page_title'] == page.title()
        page.goto(site + '/cuenta', wait_until='networkidle')
        assert len(calls) == 1 and views(page) == []
        with page.expect_request('https://www.googletagmanager.com/**'):
            page.locator('nav[aria-label=Principal]').get_by_role('link', name='Tutoriales', exact=True).click()
        page.wait_for_function("(window.dataLayer||[]).some(x=>x[0]==='event')")
        assert len(calls) == 2
        page.get_by_role('button', name='Preferencias de analítica').click()
        page.get_by_role('button', name='Rechazar analítica').click()
        page.wait_for_load_state('networkidle')
        assert len(calls) == 2 and views(page) == []
        assert not errors
        context.close(); browser.close()


def test_direct_and_allowlisted_campaigns(site):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for suffix, campaign in [('/', False), ('/?utm_source=newsletter&utm_medium=email&utm_campaign=guia-pdf&email=private#secret', True)]:
            context, calls = context_for(browser); page = context.new_page()
            page.goto(site + suffix, wait_until='networkidle'); assert calls == []
            page.get_by_role('button', name='Aceptar analítica').click()
            page.wait_for_function("(window.dataLayer||[]).some(x=>x[0]==='event')")
            data = config(page)
            assert data['page_referrer'] == '' and data['page_location'] == site + '/'
            assert ('campaign_source' in data) == campaign
            if campaign: assert data['campaign_source'] == 'newsletter' and data['campaign_name'] == 'guia-pdf'
            assert 'private' not in json.dumps(data)
            context.close()
        browser.close()


def test_invalid_future_consent_does_not_load_google(site):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(); context, calls = context_for(browser)
        context.add_init_script("localStorage.setItem('foroia-analytics-consent-v1',JSON.stringify({choice:'accepted',at:Date.now()+86400000}))")
        page = context.new_page(); page.goto(site, wait_until='networkidle')
        assert page.get_by_role('button', name='Aceptar analítica').is_visible()
        assert calls == []
        context.close(); browser.close()


def test_editorial_payload_ssr_links_metadata_and_sitemap(site):
    import httpx
    from playwright.sync_api import sync_playwright
    articles = json.loads((ROOT/'editorial/phase1/publication.json').read_text(encoding='utf-8'))
    with httpx.Client(base_url=site, trust_env=False) as client, sync_playwright() as p:
        browser = p.chromium.launch()
        context, calls = context_for(browser)
        page = context.new_page()
        sitemap = client.get('/sitemaps/articles/1')
        assert sitemap.status_code == 200
        for article in articles:
            path = '/articulos/' + article['slug']
            response = client.get(path)
            assert response.status_code == 200, response.text
            assert article['title'] in response.text  # SSR, before executing JS
            assert site + path in sitemap.text
            page.goto(site + path, wait_until='networkidle')
            assert page.locator('h1').inner_text() == article['title']
            assert 'Redacción de Foro IA al Día' in page.locator('.article-byline').inner_text()
            assert 'asistencia de IA' not in page.locator('.article-byline').inner_text()
            assert page.locator('meta[name="description"]').get_attribute('content') == article['summary']
            assert page.locator('link[rel="canonical"]').get_attribute('href') == site + path
            assert page.locator('time[datetime]').first.get_attribute('datetime') == '2026-10-23T12:00:00.123Z'
            assert page.locator('pre[aria-label]').count() == 0
            assert page.locator('.article-cover img').get_attribute('loading') == 'eager'
            for index in range(page.locator('pre').count()):
                code = page.locator('pre').nth(index)
                code.focus()
                assert code.evaluate('(el)=>el===document.activeElement')
            assert page.locator('link[rel="prefetch"][as]').count() == 0
            assert page.locator('link[rel="modulepreload"]').count() > 0
            assert page.locator('.prose a[href^="/articulos/"]').count() == 2
            assert not page.locator('.prose').inner_text().endswith('Estado editorial:')
            for target in page.locator('.prose a[href^="/recursos/"]').evaluate_all('(a)=>a.map(x=>x.getAttribute("href"))'):
                assert client.get(target).status_code == 200
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert calls == []
        context.close(); browser.close()


def test_section_headings_and_information_social_metadata(site):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(); context, calls = context_for(browser); page = context.new_page()
        for section in ['herramientas', 'programacion', 'tutoriales']:
            page.goto(site + '/' + section, wait_until='networkidle')
            assert page.locator('h1').count() == 1
            assert page.locator('.article-card h2').count() > 0
            assert page.locator('.article-card h3').count() == 0
        page.goto(site, wait_until='networkidle')
        assert page.locator('h1').inner_text() == 'La inteligencia artificial,\nexplicada con calma.'
        assert page.locator('.article-card h3').count() > 0
        for slug in ['contacto', 'criterio-editorial', 'normas', 'cookies']:
            page.goto(site + '/informacion/' + slug, wait_until='networkidle')
            for key in ['title', 'description', 'type', 'url', 'image']:
                assert page.locator('meta[property="og:' + key + '"]').get_attribute('content')
            assert page.locator('meta[property="og:url"]').get_attribute('content') == site + '/informacion/' + slug
        assert calls == []
        context.close(); browser.close()


def test_export_ssr_for_independent_validators(site):
    import httpx
    target = ROOT/'.local/seo-fix-20261023/ssr'
    target.mkdir(parents=True, exist_ok=True)
    articles = json.loads((ROOT/'editorial/phase1/publication.json').read_text(encoding='utf-8'))
    paths = ['/', '/actualidad', '/herramientas', '/programacion', '/tutoriales']
    paths += ['/informacion/' + slug for slug in ['contacto', 'criterio-editorial', 'normas', 'cookies']]
    paths += ['/articulos/' + a['slug'] for a in articles]
    manifest = []
    with httpx.Client(base_url=site, trust_env=False) as c:
        for i, path in enumerate(paths):
            r = c.get(path)
            assert r.status_code == 200
            filename = str(i) + '.html'
            (target/filename).write_text(r.text, encoding='utf-8')
            manifest.append({'path': path, 'filename': filename})
    (target/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


def test_accessibility_seo_templates(site):
    from playwright.sync_api import sync_playwright
    script = ROOT/'.local/seo-fix-20261023/axe.min.js'
    if not script.exists():
        pytest.skip('Provide a local axe-core script for the optional browser audit')
    with sync_playwright() as p:
        browser = p.chromium.launch(); context, calls = context_for(browser); page = context.new_page()
        results = []
        for path in ['/', '/actualidad', '/herramientas', '/programacion', '/tutoriales', '/articulos/extraer-texto-pdf-python']:
            page.goto(site + path, wait_until='networkidle')
            page.add_script_tag(path=str(script))
            result = page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']}});return {violations:r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)})),incomplete:r.incomplete.map(v=>v.id)}}")
            assert result['violations'] == [], (path, result)
            assert 'aria-prohibited-attr' not in result['incomplete'], (path, result)
            results.append({'path': path, **result})
        (ROOT/'.local/seo-fix-20261023/accessibility.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
        assert calls == []
        context.close(); browser.close()


def test_research_imported_history_and_visible_refresh(site):
    from datetime import datetime, timezone
    from playwright.sync_api import sync_playwright
    import httpx
    assert httpx.get(site + '/editorial/investigacion', trust_env=False).status_code == 302
    with sync_playwright() as p:
        browser = p.chromium.launch(); context = browser.new_context()
        context.add_cookies([{'name': 'foroia_session', 'value': 'research-fixture', 'url': site}])
        page = context.new_page()
        page.clock.install(time=datetime(2026, 10, 23, 19, 0, tzinfo=timezone.utc))
        requests = []
        page.on('request', lambda r: requests.append(r.url) if '/api/editorial/research' in r.url else None)
        page.goto(site + '/editorial/investigacion', wait_until='networkidle')
        assert page.locator('h3').filter(has_text='Historial importado').count() == 2
        assert 'Ejecución en curso' not in page.locator('main').inner_text()
        assert 'prevista a las 22:30' in page.locator('main').inner_text()
        assert '0.157429' in page.locator('main').inner_text()
        page.clock.fast_forward(31_000)
        page.wait_for_timeout(200)
        assert len(requests) >= 2
        assert all('/api/editorial/research' in url for url in requests)
        payload = context.request.get(site + '/api/editorial/research').json()
        payload['runs'] = [{'id': 23, 'date': '2026-10-23', 'status': 'skipped', 'reason': 'insufficient_sources',
            'article_id': None, 'reserved_usd': '0', 'finished_at': '2026-10-23T20:30:00Z',
            'report': {'candidate_count': 9, 'fetch_failures': 1, 'source_organizations': ['ai2', 'microsoft'],
                'selection': {'selected_organizations': [], 'generation_calls_avoided': 1, 'rejected_candidates': 1,
                    'candidates': [{'topic_id':'topic-test','title':'Agentes de bases de datos','organizations':['microsoft'],
                                    'status':'rejected','reason':'insufficient_independent_topic_sources'}],
                    'excluded_documents':[{'url':'https://blog.google/copy','reason':'same_origin'}]},
                'fetch_errors': [{'url': 'https://openai.com/index/example', 'stage': 'article', 'code': 'http_status', 'http_status': 403}]}}]
        context.route('**/api/editorial/research', lambda route: route.fulfill(json=payload))
        page.get_by_role('button', name='Actualizar', exact=True).click()
        page.get_by_text('Organizaciones confirmadas: ai2, microsoft.', exact=True).wait_for()
        page.get_by_text('Ver consultas fallidas', exact=True).click()
        assert 'HTTP 403' in page.locator('details').filter(has_text='Ver consultas fallidas').inner_text()
        assert 'denegó el acceso' in page.locator('details').filter(has_text='Ver consultas fallidas').inner_text()
        page.get_by_text('Selección de temas y fuentes', exact=True).click()
        assert '1 llamada inicial de redacción evitada' in page.locator('main').inner_text()
        assert 'Descartado: faltan organizaciones independientes' in page.locator('main').inner_text()
        assert 'Contenido duplicado o procedencia compartida' in page.locator('main').inner_text()
        context.close(); browser.close()
