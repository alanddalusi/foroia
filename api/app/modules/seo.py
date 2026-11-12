"""Bounded public sitemap reads, not forwarded by the web API proxy."""
from fastapi import APIRouter, Query
from sqlalchemy import func, select
from app.models import Article, Topic
from app.modules.articles.editorial import DB

router = APIRouter(prefix='/seo', tags=['seo'])


@router.get('/inventory')
async def inventory(db: DB):
    return {
        'articles': await db.scalar(select(func.count()).select_from(Article).where(Article.status == 'published')),
        'topics': await db.scalar(select(func.count()).select_from(Topic).where(Topic.published.is_(True))),
        'sections': (await db.scalars(select(Article.section).where(Article.status == 'published').distinct())).all(),
    }


@router.get('/entries')
async def entries(db: DB, kind: str = Query(pattern='^(articles|topics)$'), page: int = Query(1, ge=1, le=10000)):
    model = Article if kind == 'articles' else Topic
    public = Article.status == 'published' if kind == 'articles' else Topic.published.is_(True)
    stamp = Article.updated_at if kind == 'articles' else Topic.created_at
    rows = (await db.execute(select(model.slug, stamp).where(public).order_by(model.id)
        .offset((page - 1) * 5000).limit(5000))).all()
    return [{'slug': slug, 'updated_at': date} for slug, date in rows]
