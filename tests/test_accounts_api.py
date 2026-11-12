"""Permisos, sesiones, CSRF, recuperación y moderación con DB aislada."""
import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import select

from test_articles_api import client, article, publish, AUTH
from app.core.config import get_settings
from app.core import db as core_db, limits
from app.models import AccountToken, Article, Comment, MailOutbox, User, UserSession, utcnow
from app.modules.accounts import PH, digest

ORIGIN = {'Origin': 'http://localhost:3000'}
PASSWORD = 'contraseña-local-segura-123'


def database(operation):
    async def run():
        async for db in app_override()():
            value = await operation(db)
            await db.commit()
            return value
    return asyncio.run(run())


def app_override():
    from app.main import app
    return app.dependency_overrides[core_db.get_db]


class FakeRedis:
    def __init__(self): self.values = {}
    async def eval(self, script, keys, key, seconds):
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]


@pytest.fixture
def account_client(client, monkeypatch):
    monkeypatch.setenv('LEGACY_EDITORIAL_ENABLED', 'false')
    get_settings.cache_clear()
    monkeypatch.setattr(limits, 'get_redis', lambda: fake)
    fake = FakeRedis()
    yield client
    get_settings.cache_clear()


def seed_user(email='member@example.test', role='member', verified=True, blocked=False):
    async def create(db):
        user = User(email=email, display_name='Persona de prueba', password_hash=PH.hash(PASSWORD), role=role, verified=verified, blocked=blocked)
        db.add(user)
        await db.flush()
        return user.id
    return database(create)


def session(client, email='member@example.test'):
    response = client.post('/auth/login', json={'email': email, 'password': PASSWORD}, headers=ORIGIN)
    assert response.status_code == 200, response.text
    cookies = response.cookies
    return {'Cookie': '; '.join(f'{k}={v}' for k, v in cookies.items()), 'X-CSRF-Token': cookies['foroia_csrf'], **ORIGIN}


def seed_article():
    async def create(db):
        obj = Article(**article(), status='published', published_at=utcnow())
        db.add(obj); await db.flush()
        return obj.id
    return database(create)


def decision(client, cid, headers):
    row = next(c for c in client.get('/moderation/comments', headers=headers).json()['items'] if c['id'] == cid)
    return {'status': 'approved', 'version': row['version']}


def mail_token(purpose='verify'):
    async def read(db):
        row = await db.scalar(select(MailOutbox).order_by(MailOutbox.id.desc()).limit(1))
        return row.body.split(f'#{purpose}=')[1].split()[0]
    return database(read)


def test_closed_registration_does_not_create_user_or_mail(account_client, monkeypatch):
    monkeypatch.setenv('REGISTRATION_ENABLED', 'false')
    get_settings.cache_clear()
    seed_user()
    response = account_client.post('/auth/register', json={
        'email': 'closed@example.test', 'password': PASSWORD, 'display_name': 'Nueva persona',
    }, headers=ORIGIN)
    assert response.status_code == 503
    async def inspect(db):
        assert await db.scalar(select(User).where(User.email == 'closed@example.test')) is None
        assert await db.scalar(select(MailOutbox.id)) is None
    database(inspect)
    # Cerrar altas no bloquea el acceso administrativo/de cuentas existentes.
    headers = session(account_client)
    assert account_client.get('/auth/me', headers=headers).status_code == 200


def test_disabled_account_email_creates_no_tokens_or_messages(account_client, monkeypatch):
    monkeypatch.setenv('ACCOUNT_EMAIL_ENABLED', 'false')
    get_settings.cache_clear()
    seed_user()
    for action in ['forgot', 'resend']:
        assert account_client.post('/auth/' + action, json={'email': 'member@example.test'}, headers=ORIGIN).status_code == 503
    assert account_client.post('/auth/register', json={'email': 'new@example.test', 'password': PASSWORD, 'display_name': 'Nueva'}, headers=ORIGIN).status_code == 503
    async def inspect(db):
        assert await db.scalar(select(AccountToken.token_hash)) is None
        assert await db.scalar(select(MailOutbox.id)) is None
        assert await db.scalar(select(User).where(User.email == 'new@example.test')) is None
    database(inspect)
    assert session(account_client)


def test_registration_verification_no_enumeration(account_client):
    c = account_client
    payload = {'email': 'NEW@example.test', 'password': PASSWORD, 'display_name': 'Nueva persona'}
    r = c.post('/auth/register', json=payload, headers=ORIGIN)
    assert r.status_code == 202
    token = mail_token()
    assert c.post('/auth/register', json=payload, headers=ORIGIN).json() == r.json()
    assert c.post('/auth/register', json=payload | {'role': 'admin'}, headers=ORIGIN).status_code == 422
    h = session(c, 'new@example.test')
    assert c.get('/auth/me', headers=h).json()['verified'] is False
    assert c.post('/auth/verify', json={'token': token}, headers=ORIGIN).status_code == 200
    assert c.post('/auth/verify', json={'token': token}, headers=ORIGIN).status_code == 400
    assert c.get('/auth/me', headers=h).json()['verified'] is True


def test_login_logout_csrf_and_cookie_flags(account_client):
    c = account_client; seed_user()
    r = c.post('/auth/login', json={'email': 'member@example.test', 'password': PASSWORD}, headers=ORIGIN)
    assert r.status_code == 200
    cookie = r.headers.get_list('set-cookie')[0]
    assert 'HttpOnly' in cookie and 'SameSite=lax' in cookie
    h = {'Cookie': '; '.join(f'{k}={v}' for k, v in r.cookies.items()), **ORIGIN}
    assert c.post('/auth/logout', json={}, headers=h).status_code == 403
    h['X-CSRF-Token'] = r.cookies['foroia_csrf']
    assert c.post('/auth/logout', json={}, headers=h | {'Origin': 'https://evil.test'}).status_code == 403
    assert c.post('/auth/logout', json={}, headers=h).status_code == 200
    assert c.get('/auth/me', headers=h).status_code == 401


def test_reset_revokes_sessions_and_token_is_single_use(account_client):
    c = account_client; seed_user(); h = session(c)
    assert c.post('/auth/forgot', json={'email': 'member@example.test'}, headers=ORIGIN).status_code == 202
    raw = mail_token('reset')
    assert c.post('/auth/reset', json={'token': raw, 'password': PASSWORD + 'x'}, headers=ORIGIN).status_code == 200
    assert c.get('/auth/me', headers=h).status_code == 401
    assert c.post('/auth/reset', json={'token': raw, 'password': PASSWORD}, headers=ORIGIN).status_code == 400


@pytest.mark.parametrize('role,allowed', [('member', False), ('moderator', False), ('editor', True), ('admin', True)])
def test_editorial_roles(account_client, role, allowed):
    c = account_client; seed_user(role=role); h = session(c)
    assert c.get('/editorial/articles', headers=h).status_code == (200 if allowed else 403)
    assert c.post('/editorial/articles', json=article(), headers=h).status_code == (201 if allowed else 403)
    assert c.post('/editorial/articles', json=article(slug='sin-csrf'), headers={k:v for k,v in h.items() if k != 'X-CSRF-Token'}).status_code == 403


def test_comments_pending_moderated_edit_and_idor(account_client):
    c = account_client; seed_user(); seed_user('admin@example.test', 'admin'); seed_user('other@example.test')
    seed_article(); member = session(c); admin = session(c, 'admin@example.test'); other = session(c, 'other@example.test')
    path = '/articles/nuevo-modelo-abierto/comments'
    assert c.post(path, json={'body': 'Hola'}).status_code == 401
    created = c.post(path, json={'body': '<script>alert(1)</script>'}, headers=member)
    assert created.status_code == 201
    cid = created.json()['id']
    assert c.get(path).json()['items'] == []
    assert c.get('/moderation/comments', headers=member).status_code == 403
    assert c.post(f'/moderation/comments/{cid}', json={'status': 'approved'}, headers=member).status_code == 403
    assert c.patch(f'/comments/{cid}', json={'body': 'Robado'}, headers=other).status_code == 404
    assert c.delete(f'/comments/{cid}', json={}, headers=other).status_code == 404
    assert c.post(f'/moderation/comments/{cid}', json=decision(c, cid, admin), headers=admin).status_code == 200
    public = c.get(path).json()['items']
    assert public[0]['body'] == '<script>alert(1)</script>' and 'email' not in public[0]
    assert c.patch(f'/comments/{cid}', json={'body': 'Corregido'}, headers=member).status_code == 200
    assert c.get(path).json()['items'] == []
    assert c.post(f'/moderation/comments/{cid}', json=decision(c, cid, admin), headers=admin).status_code == 200
    assert c.delete(f'/comments/{cid}', json={}, headers=member).status_code == 200
    assert c.get(path).json()['items'] == []


def test_unverified_blocked_and_closed_articles(account_client):
    c = account_client; seed_user(verified=False); aid = seed_article(); h = session(c)
    path = '/articles/nuevo-modelo-abierto/comments'
    assert c.post(path, json={'body': 'Hola'}, headers=h).status_code == 403
    async def change(db):
        u = await db.get(User, 1); u.verified = True
        a = await db.get(Article, aid); a.comments_enabled = False
    database(change)
    assert c.post(path, json={'body': 'Hola'}, headers=h).status_code == 403
    async def block(db):
        u = await db.get(User, 1); u.blocked = True
    database(block)
    assert c.get('/auth/me', headers=h).status_code == 403


def test_archive_hides_comments_and_rejects_new_ones(account_client):
    c = account_client; seed_user(); aid = seed_article(); h = session(c)
    path = '/articles/nuevo-modelo-abierto/comments'
    assert c.post(path, json={'body': 'Pregunta útil'}, headers=h).status_code == 201
    async def archive(db):
        a = await db.get(Article, aid); a.status = 'archived'
    database(archive)
    assert c.get(path).status_code == 404
    assert c.post(path, json={'body': 'Otra pregunta'}, headers=h).status_code == 404


@pytest.mark.parametrize('body', ['', '   ', 'a' * 5001, 'a\x00'])
def test_comment_validation(account_client, body):
    c = account_client; seed_user(); seed_article(); h = session(c)
    assert c.post('/articles/nuevo-modelo-abierto/comments', json={'body': body}, headers=h).status_code == 422


def test_rate_limit_shared_and_redis_failure(account_client, monkeypatch):
    c = account_client; seed_user()
    for _ in range(10):
        assert c.post('/auth/login', json={'email': 'member@example.test', 'password': PASSWORD + 'bad'}, headers=ORIGIN).status_code == 401
    assert c.post('/auth/login', json={'email': 'member@example.test', 'password': PASSWORD}, headers=ORIGIN).status_code == 429
    class Broken:
        async def eval(self, *args):
            from redis.exceptions import ConnectionError
            raise ConnectionError()
    monkeypatch.setattr(limits, 'get_redis', lambda: Broken())
    assert c.post('/auth/register', json={'email': 'new@example.test', 'password': PASSWORD, 'display_name': 'Nueva persona'}, headers=ORIGIN).status_code == 503


def test_expired_session_and_token(account_client):
    c = account_client; seed_user(); h = session(c)
    async def expire(db):
        row = await db.scalar(select(UserSession)); row.expires_at = utcnow() - timedelta(seconds=1)
    database(expire)
    assert c.get('/auth/me', headers=h).status_code == 401
    c.post('/auth/forgot', json={'email': 'member@example.test'}, headers=ORIGIN)
    raw = mail_token('reset')
    async def expire_token(db):
        row = await db.get(AccountToken, digest(raw)); row.expires_at = utcnow() - timedelta(seconds=1)
    database(expire_token)
    assert c.post('/auth/reset', json={'token': raw, 'password': PASSWORD}, headers=ORIGIN).status_code == 400


def test_comment_cursor_visibility_and_duplicate(account_client):
    c = account_client; uid = seed_user(); aid = seed_article(); h = session(c)
    async def seed(db):
        now = utcnow()
        for n in range(23):
            db.add(Comment(user_id=uid, article_id=aid, body=f'Comentario {n}', status='approved' if n < 22 else 'pending', created_at=now))
    database(seed)
    path = '/articles/nuevo-modelo-abierto/comments'
    first = c.get(path + '?limit=20').json()
    second = c.get(path + '?limit=20&cursor=' + first['next_cursor']).json()
    assert len(first['items']) == 20 and len(second['items']) == 2
    assert len({v['id'] for v in first['items'] + second['items']}) == 22
    assert c.get(path + '?cursor=not-a-cursor').status_code == 422
    assert c.get(path + '?limit=51').status_code == 422
    assert c.post(path, json={'body': 'Pregunta nueva', 'user_id': 999}, headers=h).status_code == 422
    assert c.post(path, json={'body': 'Pregunta nueva'}, headers=h).status_code == 201
    assert c.post(path, json={'body': 'Pregunta nueva'}, headers=h).status_code == 409


def test_moderator_cannot_approve_a_version_changed_after_review(account_client):
    c = account_client; seed_user(); seed_user('admin@example.test', 'admin'); seed_article()
    member, admin = session(c), session(c, 'admin@example.test')
    created = c.post('/articles/nuevo-modelo-abierto/comments', json={'body': 'Primera versión'}, headers=member)
    cid = created.json()['id']
    stale = decision(c, cid, admin)
    assert c.patch(f'/comments/{cid}', json={'body': 'Versión cambiada después de revisar'}, headers=member).status_code == 200
    assert c.post(f'/moderation/comments/{cid}', json=stale, headers=admin).status_code == 409
    assert c.get('/articles/nuevo-modelo-abierto/comments').json()['items'] == []
    assert c.post(f'/moderation/comments/{cid}', json=decision(c, cid, admin), headers=admin).status_code == 200
