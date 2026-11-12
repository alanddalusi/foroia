"""Recorrido real en Chromium, escritorio y móvil. Optativo y solo local.

Los artículos de prueba se identifican como tales y se archivan al terminar.
No se guardan trazas, cookies ni capturas de contraseñas.
"""
import json
import os
import re
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.environ.get('FOROIA_BROWSER') != '1', reason='Requiere FOROIA_BROWSER=1, Chromium y servicios locales')


def credentials():
    env = {}
    for line in (Path(__file__).resolve().parents[1] / '.env').read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1); env[key] = value
    return env.get('BOOTSTRAP_EMAIL', 'editor@localhost.test'), env['EDITORIAL_PASSWORD']


@pytest.mark.parametrize('width,height', [(1280, 900), (390, 844)])
def test_editorial_browser_keyboard_and_mobile(width, height):
    from playwright.sync_api import sync_playwright, expect
    email, password = credentials()
    slug = 'prueba-navegador-' + uuid.uuid4().hex[:10]
    article_id = None
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={'width': width, 'height': height}, base_url='http://localhost:3000')
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        try:
            artifacts = Path('.local/design'); artifacts.mkdir(parents=True, exist_ok=True)
            page.goto('/')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(artifacts / f'home-before-publication-{width}.png'), full_page=True)
            page.goto('/editorial')
            expect(page).to_have_url(re.compile('/cuenta$'))
            page.get_by_label('Correo electrónico').fill(email)
            page.get_by_label('Contraseña', exact=True).fill(password)
            page.get_by_role('button', name='Iniciar sesión', exact=True).click()
            expect(page.get_by_role('button', name='Cerrar sesión')).to_be_visible()
            page.get_by_role('link', name='Panel editorial', exact=True).click()
            expect(page.get_by_role('heading', name='Panel editorial')).to_be_visible()
            page.get_by_role('link', name='Investigación diaria', exact=True).click()
            expect(page.get_by_role('heading', name='Investigación diaria')).to_be_visible()
            expect(page.get_by_text('Presupuesto mensual:', exact=False)).to_be_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            if width == 1280:
                pause = page.get_by_role('button', name='Pausar investigación', exact=True)
                if pause.count():
                    pause.focus(); page.keyboard.press('Enter')
                    expect(page.get_by_role('button', name='Reanudar investigación')).to_be_visible()
                    page.get_by_role('button', name='Reanudar investigación').click()
                    expect(page.get_by_role('button', name='Pausar investigación')).to_be_visible()
            page.screenshot(path=str(artifacts / f'research-{width}.png'), full_page=True)
            page.get_by_role('link', name='Volver al panel editorial').click()
            page.get_by_role('link', name='Nuevo artículo').click()
            contrast = page.get_by_role('button', name='Crear borrador').evaluate('''el => {
                const lum = color => color.match(/[0-9.]+/g).slice(0,3).map(Number).map(v => v/255).map(v => v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4).reduce((s,v,i)=>s+v*[0.2126,0.7152,0.0722][i],0);
                const style=getComputedStyle(el), a=lum(style.color), b=lum(style.backgroundColor);
                return (Math.max(a,b)+0.05)/(Math.min(a,b)+0.05);
            }''')
            assert contrast >= 4.5
            title = page.get_by_label('Título', exact=True)
            title.focus(); page.keyboard.type('Prueba de navegador y teclado')
            page.get_by_label('Slug (URL)').fill(slug)
            page.get_by_label('Autor', exact=True).fill('Prueba automatizada')
            page.get_by_label('Resumen / meta descripción').fill('Artículo temporal de verificación del navegador; se retira automáticamente al terminar las pruebas.')
            page.get_by_label('Cuerpo', exact=False).fill('## Prueba\n\nTexto seguro <script>window.injection=true</script>.\n\n' + 'Contenido de prueba. ' * 30)
            page.get_by_role('button', name='Añadir fuente').click()
            page.get_by_label('Título', exact=True).nth(1).fill('Fuente de prueba')
            page.get_by_label('URL', exact=True).fill('https://example.com/')
            page.get_by_role('button', name='Crear borrador').focus(); page.keyboard.press('Enter')
            expect(page).to_have_url(re.compile(r'/editorial/\d+$'))
            article_id = int(page.url.rsplit('/', 1)[1])
            page.get_by_role('button', name='Previsualizar', exact=True).click()
            expect(page.get_by_role('heading', name='Prueba de navegador y teclado')).to_have_count(2)
            assert page.evaluate('window.injection') is None
            page.get_by_role('button', name='Volver a editar').click()
            page.get_by_role('button', name='Enviar a revisión').focus(); page.keyboard.press('Enter')
            expect(page.get_by_role('status')).to_contain_text('En revisión')
            page.once('dialog', lambda dialog: dialog.accept())
            page.get_by_role('button', name='Aprobar y publicar').focus(); page.keyboard.press('Enter')
            expect(page.get_by_role('status')).to_contain_text('Publicado')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            artifacts = Path('.local/browser'); artifacts.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(artifacts / f'editorial-{width}.png'), full_page=True)
            public = context.new_page()
            response = public.goto(f'/articulos/{slug}')
            assert response.status == 200
            expect(public.get_by_role('heading', name='Prueba de navegador y teclado')).to_be_visible()
            assert public.evaluate('window.injection') is None
            assert public.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert public.locator('.prose').evaluate('el => parseFloat(getComputedStyle(el).fontSize)') >= 18
            # Navegación por teclado: el primer enlace permite saltar al contenido.
            public.keyboard.press('Tab')
            expect(public.get_by_role('link', name='Saltar al contenido')).to_be_focused()
            public.keyboard.press('Enter')
            assert public.evaluate('location.hash') == '#contenido'
            expect(public.locator('main')).to_be_focused()
            public.screenshot(path=str(artifacts / f'article-{width}.png'), full_page=True)
            public.goto('/')
            expect(public.get_by_role('heading', name='Prueba de navegador y teclado')).to_be_visible()
            assert public.evaluate('document.documentElement.scrollWidth <= innerWidth')
            public.screenshot(path=f'.local/design/home-published-{width}.png', full_page=True)
            # Reflujo de la portada a 320 px sin perder navegación ni contenido.
            public.set_viewport_size({'width': 320, 'height': 844})
            assert public.evaluate('document.documentElement.scrollWidth <= innerWidth')
            expect(public.get_by_role('navigation', name='Principal')).to_be_visible()
            page.get_by_role('button', name='Retirar (archivar)').focus(); page.keyboard.press('Enter')
            expect(page.get_by_role('status')).to_contain_text('Archivado')
            assert public.goto(f'/articulos/{slug}').status == 404
            assert slug not in context.request.get('/sitemaps/articles/1').text()
            assert not errors, errors
        finally:
            if article_id:
                csrf = next((c['value'] for c in context.cookies() if c['name'] == 'foroia_csrf'), '')
                context.request.post(f'/api/editorial/articles/{article_id}/status', data={'status': 'archived'}, headers={'Origin': 'http://localhost:3000', 'X-CSRF-Token': csrf})
            context.close(); browser.close()


def test_registration_email_comments_and_moderation_browser():
    from playwright.sync_api import sync_playwright, expect
    admin_email, admin_password = credentials()
    suffix = uuid.uuid4().hex[:10]
    member_email = f'browser-{suffix}@localhost.test'
    member_password = uuid.uuid4().hex + '-Test'
    slug = 'prueba-comentarios-' + suffix
    text = 'Comentario de prueba <img src=x onerror="window.injection=true"> ' + suffix
    aid = None
    with sync_playwright() as p:
        browser = p.chromium.launch()
        admin = browser.new_context(base_url='http://localhost:3000')
        member = browser.new_context(base_url='http://localhost:3000', viewport={'width': 390, 'height': 844})
        guest = browser.new_context(base_url='http://localhost:3000')
        page = member.new_page()
        try:
            login_response = admin.request.post('/api/community/auth/login', data={'email': admin_email, 'password': admin_password}, headers={'Origin': 'http://localhost:3000'})
            assert login_response.status == 200, 'No se pudo iniciar la sesión administrativa'
            csrf = next(c['value'] for c in admin.cookies() if c['name'] == 'foroia_csrf')
            headers = {'Origin': 'http://localhost:3000', 'X-CSRF-Token': csrf}
            article = {'slug': slug, 'title': 'Prueba de comentarios moderados', 'summary': 'Artículo temporal para comprobar comentarios, correo de verificación y permisos de moderación.', 'body': 'Explicación de prueba. ' * 30, 'section': 'tutoriales', 'author_name': 'Prueba automatizada', 'sources': [{'title': 'Fuente de prueba', 'url': 'https://example.com/', 'language': 'en'}]}
            response = admin.request.post('/api/editorial/articles', data=article, headers=headers)
            assert response.status == 201
            aid = response.json()['id']
            for status in ('review', 'published'):
                assert admin.request.post(f'/api/editorial/articles/{aid}/status', data={'status': status}, headers=headers).status == 200
            page.goto('/cuenta')
            page.get_by_label('Acción').select_option('register')
            page.get_by_label('Correo electrónico').fill(member_email)
            page.get_by_label('Nombre público').fill('Prueba automatizada')
            page.get_by_label('Contraseña', exact=True).fill(member_password)
            page.get_by_role('button', name='Crear cuenta', exact=True).click()
            expect(page.get_by_role('status')).to_contain_text('verificación')
            link = None
            for _ in range(30):
                messages = member.request.get('http://localhost:8025/api/v1/messages').json()['messages']
                found = next((m for m in messages if any(t['Address'] == member_email for t in m['To'])), None)
                if found:
                    mail = member.request.get(f"http://localhost:8025/api/v1/message/{found['ID']}").json()
                    link = re.search(r'http://localhost:3000/cuenta#verify=[A-Za-z0-9_-]+', mail['Text']).group()
                    break
                page.wait_for_timeout(1000)
            assert link, 'No se recibió el correo en el buzón local'
            page.goto(link)
            page.get_by_role('button', name='Verificar correo', exact=True).click()
            expect(page.get_by_role('status')).to_contain_text('Correo verificado')
            page.get_by_label('Correo electrónico').fill(member_email)
            page.get_by_label('Contraseña', exact=True).fill(member_password)
            page.get_by_role('button', name='Iniciar sesión', exact=True).click()
            expect(page.get_by_role('button', name='Cerrar sesión')).to_be_visible()
            assert member.request.get('/api/editorial/articles').status == 403
            page.goto(f'/articulos/{slug}')
            page.get_by_label('Tu comentario').fill(text)
            page.get_by_role('button', name='Enviar comentario').click()
            expect(page.get_by_role('status')).to_contain_text('moderación')
            assert text not in guest.request.get(f'/articulos/{slug}').text()
            mod_page = admin.new_page(); mod_page.goto('/moderacion')
            row = mod_page.locator('article').filter(has_text=text)
            row.get_by_role('button', name='Aprobar', exact=True).click()
            expect(mod_page.get_by_role('status')).to_contain_text('Decisión guardada')
            public = guest.new_page(); public.goto(f'/articulos/{slug}')
            expect(public.get_by_text(text, exact=True)).to_be_visible()
            assert public.evaluate('window.injection') is None
            page.goto('/cuenta')
            page.once('dialog', lambda dialog: dialog.accept('Comentario corregido de prueba ' + suffix))
            page.get_by_role('button', name='Editar', exact=True).click()
            expect(page.get_by_role('status')).to_contain_text('moderación')
            public.reload()
            expect(public.get_by_text(text, exact=True)).to_have_count(0)
            page.get_by_role('button', name='Retirar', exact=True).click()
            expect(page.get_by_role('status')).to_contain_text('retirado')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        finally:
            if aid:
                admin.request.post(f'/api/editorial/articles/{aid}/status', data={'status': 'archived'}, headers=headers)
            admin.close(); member.close(); guest.close(); browser.close()
