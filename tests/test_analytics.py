from datetime import timedelta

from test_articles_api import client, AUTH, publish
from test_accounts_api import account_client, seed_user, session, database
from app.models import DailyPageView
from app.modules.analytics import today

INTERNAL = {'X-Internal-Token': AUTH['X-Editorial-Token']}


def test_internal_only_and_valid_paths(client):
    assert client.post('/internal/page-view', json={'path': '/'}).status_code == 403
    for path in ['/cuenta', '/editorial', '/articulos/missing', '/?email=private', '/blog/missing']:
        assert client.post('/internal/page-view', json={'path': path}, headers=INTERNAL).status_code == 422
    assert client.post('/internal/page-view', json={'path': '/', 'ip': 'private'}, headers=INTERNAL).status_code == 422
    assert client.get('/editorial/analytics').status_code == 401


def test_aggregate_periods_and_article_visibility(client):
    aid = publish(client)
    for path in ['/', '/', '/articulos/nuevo-modelo-abierto']:
        assert client.post('/internal/page-view', json={'path': path}, headers=INTERNAL).status_code == 204
    async def previous(db):
        db.add(DailyPageView(day=today() - timedelta(days=7), path='/', views=4))
    database(previous)
    r = client.get('/editorial/analytics?days=7', headers=AUTH)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['views'] == 3 and data['previous_views'] == 4
    assert len(data['series']) == 7 and data['series'][-1]['views'] == 3
    assert data['top_articles'][0]['views'] == 1 and data['states']['published'] == 1
    assert data['series'][-1]['published'] == 1
    assert client.get('/editorial/analytics?days=1000', headers=AUTH).status_code == 422
    client.post(f'/editorial/articles/{aid}/status', json={'status': 'archived'}, headers=AUTH)
    assert client.post('/internal/page-view', json={'path': '/articulos/nuevo-modelo-abierto'}, headers=INTERNAL).status_code == 422
    data = client.get('/editorial/analytics?days=7', headers=AUTH).json()
    assert data['views'] == 3 and data['top_articles'] == []


def test_statistics_roles(account_client):
    seed_user(role='member')
    assert account_client.get('/editorial/analytics', headers=session(account_client)).status_code == 403
    seed_user(email='editor@example.test', role='editor')
    r = account_client.get('/editorial/analytics', headers=session(account_client, 'editor@example.test'))
    assert r.status_code == 200 and r.json()['views'] == 0
    assert r.headers['cache-control'] == 'no-store'
