"""Lectura pública de artículos: solo contenido con estado `published`."""
import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import Integer, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import SECTIONS, Article, ArticleAsset
from app.modules.articles.schemas import (
    SLUG_PATTERN,
    ArticleDetailOut,
    ArticleOut,
    ArticlePage,
    ArticleSummaryOut,
    Section,
    SectionOut,
    SitemapEntry,
)

router = APIRouter(tags=["articles"])
DB = Annotated[AsyncSession, Depends(get_db)]
PUBLISHED = Article.status == "published"

@router.get('/article-assets/{key}')
async def article_asset(key:str,request:Request,db:DB):
    if not re.fullmatch(r'[a-f0-9]{32}-(?:480|800|1200)\.(?:webp|png)',key):raise HTTPException(404,'Imagen no encontrada')
    asset=await db.scalar(select(ArticleAsset).join(Article,Article.id==ArticleAsset.article_id).where(ArticleAsset.key==key,PUBLISHED))
    if not asset:raise HTTPException(404,'Imagen no encontrada')
    etag='"'+asset.sha256+'"'
    headers={'ETag':etag,'X-Content-Type-Options':'nosniff','Cache-Control':'no-store'}
    if request.headers.get('if-none-match')==etag:return Response(status_code=304,headers=headers)
    return Response(asset.content,media_type=asset.content_type,headers=headers)


@router.get("/sections", response_model=list[SectionOut])
async def sections():
    return [SectionOut(slug=slug, **data) for slug, data in SECTIONS.items()]


@router.get("/articles", response_model=ArticlePage)
async def list_articles(
    db: DB,
    section: Section | None = None,
    limit: int = Query(12, ge=1, le=50),
    page: int = Query(1, ge=1, le=1000),
):
    query = select(Article).where(PUBLISHED)
    if section:
        query = query.where(Article.section == section)
    query = query.order_by(Article.published_at.desc(), Article.id.desc()).limit(limit + 1).offset((page - 1) * limit)
    rows = (await db.scalars(query)).all()
    return ArticlePage(
        items=[ArticleSummaryOut.model_validate(a) for a in rows[:limit]],
        page=page,
        has_next=len(rows) > limit,
    )


@router.get("/search", response_model=ArticlePage)
async def search_articles(
    db: DB,
    q: str = Query(min_length=2, max_length=80),
    page: int = Query(1, ge=1, le=20),
):
    """Búsqueda simple en artículos publicados: todas las palabras deben aparecer en título, resumen o cuerpo.

    Consulta parametrizada (LIKE con comodines escapados), tamaño y páginas acotados; sin registro de términos.
    """
    from sqlalchemy import and_, func, or_
    terms = [t for t in re.findall(r"[\wáéíóúñü+#.-]{2,40}", q.lower()) if t not in _STOPWORDS][:6]
    if not terms:
        return ArticlePage(items=[], page=page, has_next=False)
    def contains(col, term: str):
        pattern = "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        return func.lower(col).like(pattern, escape="\\")
    def like(term: str):
        return or_(*(contains(col, term) for col in (Article.title, Article.summary, Article.body)))
    limit = 12
    # Primero los artículos con más términos en el título.
    title_hits = sum(cast(contains(Article.title, t), Integer) for t in terms)
    rows = (await db.scalars(
        select(Article).where(PUBLISHED, and_(*(like(t) for t in terms)))
        .order_by(title_hits.desc(), Article.published_at.desc(), Article.id.desc())
        .limit(limit + 1).offset((page - 1) * limit)
    )).all()
    return ArticlePage(items=[ArticleSummaryOut.model_validate(a) for a in rows[:limit]], page=page, has_next=len(rows) > limit)


@router.get("/articles-sitemap", response_model=list[SitemapEntry])
async def articles_sitemap(db: DB):
    # Límite del protocolo sitemap por archivo; paginar al acercarse.
    rows = await db.execute(
        select(Article.slug, Article.section, Article.updated_at)
        .where(PUBLISHED)
        .order_by(Article.published_at.desc())
        .limit(50_000)
    )
    return [SitemapEntry.model_validate(row) for row in rows.all()]


@router.get("/articles/{slug}", response_model=ArticleDetailOut)
async def get_article(db: DB, slug: str):
    if len(slug) > 180 or not re.fullmatch(SLUG_PATTERN, slug):
        raise HTTPException(404, "Artículo no encontrado")
    article = await db.scalar(select(Article).where(Article.slug == slug, PUBLISHED))
    if article is None:
        raise HTTPException(404, "Artículo no encontrado")
    # Enlazado interno por tema: palabras compartidas en título/resumen, priorizando
    # la misma sección; sin coincidencias, los más recientes de la sección.
    pool = (await db.scalars(
        select(Article)
        .where(PUBLISHED, Article.id != article.id)
        .order_by(Article.published_at.desc())
        .limit(80)
    )).all()
    def words(text: str) -> set[str]:
        return {w for w in re.findall(r"[a-záéíóúñü0-9]+", text.lower()) if len(w) > 3 and w not in _STOPWORDS}
    own = words(article.title)
    scored = [(len(own & words(r.title)) * 2 + (1 if r.section == article.section else 0), i, r)
              for i, r in enumerate(pool)]
    related = [r for score, _, r in sorted(scored, key=lambda t: (-t[0], t[1])) if score >= 2][:4]
    if len(related) < 3:
        related += [r for r in pool if r.section == article.section and r not in related][:3 - len(related)]
    base = ArticleOut.model_validate(article).model_dump()
    return ArticleDetailOut(**base, related=[ArticleSummaryOut.model_validate(r) for r in related])


_STOPWORDS = {"como", "cómo", "para", "con", "una", "unos", "unas", "los", "las", "del", "que", "qué",
              "sin", "antes", "desde", "sus", "por", "entre", "sobre", "tus", "este", "esta", "cada", "puede"}
