"""Homepage site identity in real Nuxt SSR and after client navigation."""
import os
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest

from test_research import client, database
from test_editorial_http import http_database
from app.research.publication import Page

pytestmark = pytest.mark.skipif(
    os.environ.get('FOROIA_ANALYTICS_LOCAL') != '1', reason='Requires local Nuxt build'
)


def test_home_identity_survives_ssr_hydration_and_navigation(http_database, tmp_path):
    mutex = threading.Lock()

    class API(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            with mutex:
                response = http_database.get(self.path)
            self.send_response(response.status_code)
            self.send_header('Content-Type', response.headers.get('content-type', 'application/json'))
            self.end_headers()
            self.wfile.write(response.content)

    server = ThreadingHTTPServer(('127.0.0.1', 0), API)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    env = {**os.environ, 'NITRO_HOST': '127.0.0.1', 'NITRO_PORT': str(port),
           'NUXT_API_BASE': f'http://127.0.0.1:{server.server_port}',
           'NUXT_PUBLIC_SITE_URL': base, 'NUXT_PUBLIC_ANALYTICS_ENABLED': 'false',
           'NUXT_PUBLIC_GA4_ID': '', 'NUXT_ADS_PUBLISHER_ID': '', 'NUXT_EDITORIAL_API_TOKEN': ''}
    with (tmp_path / 'nuxt.log').open('w') as log:
        process = subprocess.Popen([os.environ['FOROIA_NODE_BINARY'], '.output/server/index.mjs'],
                                   cwd=Path(__file__).parents[1] / 'web', env=env, stdout=log, stderr=log)
        try:
            for _ in range(100):
                try:
                    response = httpx.get(base, trust_env=False)
                    if response.status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                assert process.poll() is None
                time.sleep(.2)
            else:
                pytest.fail('Nuxt did not start')

            def check(html):
                page = Page(html)
                sites = [item for item in page.ld if item.get('@type') == 'WebSite']
                assert len(sites) == 1
                assert sites[0] == {'@context': 'https://schema.org', '@type': 'WebSite',
                                    '@id': base + '/#website', 'name': 'Foro IA al Día',
                                    'alternateName': 'foroiaaldia.com', 'url': base + '/', 'inLanguage': 'es'}
                assert page.canonical == [base + '/']
                assert page.title == 'Foro IA al Día | Inteligencia artificial en español'
                assert page.meta['og:site_name'] == 'Foro IA al Día'
                assert 'explicada con calma.' in page.h1
                assert 'href="/foro"' in html and 'favicon.ico' in html

            check(response.text)
            from playwright.sync_api import sync_playwright
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(base, wait_until='networkidle')
                check(page.content())
                page.locator('nav a[href="/foro"]').first.click()
                page.wait_for_url(base + '/foro')
                page.locator('a.brand').click()
                page.wait_for_url(base + '/')
                page.wait_for_load_state('networkidle')
                check(page.content())
                assert not errors
                browser.close()
        finally:
            process.terminate()
            process.wait(timeout=15)
            server.shutdown()
