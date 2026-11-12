from test_articles_api import client, publish, AUTH, article
from test_accounts_api import database
from app.models import Category, Topic


def test_sitemap_visibility_and_bounds(client):
    client.post('/editorial/articles', json=article(slug='draft-not-visible'), headers=AUTH)
    aid = publish(client)
    assert client.get('/seo/inventory').json()['articles'] == 1
    entries = client.get('/seo/entries?kind=articles').json()
    assert [e['slug'] for e in entries] == ['nuevo-modelo-abierto']
    assert client.get('/seo/entries?kind=articles&page=2').json() == []
    for query in ['kind=users', 'kind=articles&page=0', 'kind=articles&page=10001']:
        assert client.get('/seo/entries?' + query).status_code == 422
    client.post(f'/editorial/articles/{aid}/status', json={'status': 'archived'}, headers=AUTH)
    assert client.get('/seo/entries?kind=articles').json() == []
    assert client.get('/seo/inventory').json()['sections'] == []


def test_sitemap_includes_topics_after_first_fifty(client):
    async def create(db):
        c = Category(slug='seo-category', name='Categoría', description='Descripción')
        db.add(c); await db.flush()
        for n in range(55):
            db.add(Topic(category_id=c.id, slug=f'public-{n}', title='Tema público', body='Texto', author_name='Prueba', published=True))
        db.add(Topic(category_id=c.id, slug='private-topic', title='Privado', body='Texto', author_name='Prueba', published=False))
    database(create)
    assert client.get('/seo/inventory').json()['topics'] == 55
    rows = client.get('/seo/entries?kind=topics').json()
    assert len(rows) == 55 and all(t['slug'] != 'private-topic' for t in rows)
    assert client.get('/categories/seo-category/topics?offset=50001').status_code == 422
