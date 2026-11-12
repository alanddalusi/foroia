"""No paid calls, no remote photographs, and no production writes."""
import asyncio
import io
from datetime import datetime,UTC
from PIL import Image
from sqlalchemy import select,func
from test_articles_api import client,article as article_payload,AUTH
from test_research import database
from app.models import Article,ArticleAsset
from app.modules.articles.media import render,ensure_media,official_videos,revenue_chart
from app.research.evidence import catalogue


def test_original_images_are_small_responsive_and_topic_specific():
    news=render('Anthropic presenta su S-1 y anuncia su intención de salir a bolsa','actualidad','anthropic-test')
    tutorial=render('Validar JSON de IA con Python','programacion','json-test')
    assert set(news)=={'480.webp','800.webp','1200.webp','1200.png'}
    assert news['1200.webp']!=tutorial['1200.webp']
    for spec,raw in news.items():
        image=Image.open(io.BytesIO(raw));w=int(spec.split('.')[0])
        assert image.size==(w,round(w*630/1200))
        assert len(raw)<180000


def test_asset_persistence_idempotency_and_private_article_visibility(client):
    stamp=datetime(2026,10,1,tzinfo=UTC)
    async def operation(db):
        row=Article(**article_payload(),status='draft',published_at=stamp,updated_at=stamp);db.add(row);await db.flush()
        await ensure_media(db,row);await db.commit();await db.refresh(row)
        assert row.updated_at.replace(tzinfo=UTC)==stamp and row.published_at.replace(tzinfo=UTC)==stamp
        await ensure_media(db,row);await db.commit()
        assert await db.scalar(select(func.count(ArticleAsset.key)))==4
        return row.id,row.media
    aid,media=database(operation);path=media['cover']['src'].removeprefix('/api')
    assert client.get(path).status_code==404
    async def publish(db):
        row=await db.get(Article,aid);row.status='published';await db.commit()
    database(publish)
    r=client.get(path);assert r.status_code==200 and r.headers['content-type']=='image/png'
    assert client.get(path,headers={'If-None-Match':r.headers['etag']}).status_code==304
    assert client.get('/articles/'+article_payload()['slug']).json()['media']['cover']['src']==media['cover']['src']
    async def archive(db):
        row=await db.get(Article,aid);row.status='archived';await db.commit()
    database(archive);assert client.get(path).status_code==404
    assert client.get('/article-assets/../../production.env').status_code==404


def test_video_provenance_must_be_an_embed_in_an_official_source():
    html=b'<iframe src="https://www.youtube.com/embed/abcdefghijk" title="Demonstration"></iframe>'
    assert official_videos(html,'https://www.anthropic.com/news/fixture')[0]['source_url']=='https://www.anthropic.com/news/fixture'
    assert official_videos(html,'https://techcrunch.com/fixture')==[]
    assert official_videos(html.replace(b'www.youtube.com',b'evil.test'),'https://openai.com/index/fixture')==[]
    assert official_videos(html.replace(b'https:',b'http:'),'https://openai.com/index/fixture')==[]
    assert official_videos(html.replace(b'www.youtube.com',b'www.youtube.com:999999'),'https://openai.com/index/fixture')==[]
    assert official_videos(html.replace(b'Demonstration',b' '),'https://openai.com/index/fixture')[0]['title']


def test_chart_requires_same_unit_period_and_numbers_already_in_article():
    url='https://techcrunch.com/fixture'
    text='The company recorded revenue of $16.3 billion for the first half of 2026, compared with $1.2 billion in the same period of 2025.'
    corpus=catalogue([{'id':1,'url':url,'text':text}])
    row=Article(**{**article_payload(),'body':'Los ingresos fueron 16,3 en 2026 frente a 1,2 en 2025.','sources':[{'url':url}]})
    chart=revenue_chart(row,corpus)[0]
    assert [(p['label'],p['value']) for p in chart['points']]==[('2025',1.2),('2026',16.3)]
    assert chart['source_url']==url and 'quote' not in chart
    unrelated=text.replace('compared with','and a debt payment of')
    assert revenue_chart(row,catalogue([{'id':1,'url':url,'text':unrelated}]))==[]
    row.body='Un artículo sin cifras verificadas';assert revenue_chart(row,corpus)==[]
