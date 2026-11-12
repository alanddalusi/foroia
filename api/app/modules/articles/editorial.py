"""Panel editorial privado (API). Requiere el token de servidor `EDITORIAL_API_TOKEN`.

Flujo: draft -> review -> published -> archived. Publicar exige revisión previa y
al menos una fuente. Cada cambio queda registrado en `audit_logs`.
Este token es una medida provisional hasta disponer de cuentas con rol `editor`.
"""
import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.models import Article, AuditLog, utcnow
from app.modules.articles.schemas import ArticleUpdate, ArticleWrite, EditorialArticleOut, StatusChange
from app.modules.accounts import current_user, csrf
from app.core.limits import client_address, limit


async def require_editor(request: Request, db: Annotated[AsyncSession, Depends(get_db)], x_editorial_token: Annotated[str | None, Header()] = None) -> str:
    settings = get_settings()
    if settings.legacy_editorial_enabled and not settings.editorial_api_token:
        raise HTTPException(503, "Panel editorial deshabilitado")
    # Compatibilidad explícita para las pruebas antiguas; desactivada por defecto.
    if settings.legacy_editorial_enabled and settings.editorial_api_token and x_editorial_token and hmac.compare_digest(x_editorial_token.encode(), settings.editorial_api_token.encode()):
        return settings.editorial_actor
    from app.modules.accounts import current_session
    session = await current_session(request, db)
    user = await current_user(db, session)
    if not user.verified or user.role not in {"editor", "admin"}:
        raise HTTPException(403, "Permisos insuficientes")
    if request.method != "GET":
        await csrf(request, session)
        await limit("editorial-user", str(user.id), 120, 300)
    return f"user:{user.id}"


router = APIRouter(prefix="/editorial", tags=["editorial"], dependencies=[Depends(require_editor)])
DB = Annotated[AsyncSession, Depends(get_db)]
Actor = Annotated[str, Depends(require_editor)]

TRANSITIONS = {
    "draft": {"review", "archived"},
    "review": {"draft", "published", "archived"},
    "published": {"archived", "draft"},
    "archived": {"draft"},
}
MIN_PUBLISH_BODY = 300


def _audit(db: AsyncSession, actor: str, action: str, article: Article, details: dict | None = None) -> None:
    db.add(AuditLog(actor=actor, action=action, entity_type="article", entity_id=article.id, details=details or {}))


async def _get(db: AsyncSession, article_id: int) -> Article:
    article = await db.scalar(select(Article).where(Article.id == article_id).with_for_update())
    if article is None:
        raise HTTPException(404, "Artículo no encontrado")
    return article


async def _commit(db: AsyncSession) -> None:
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Ya existe un artículo con ese slug") from None


@router.get("/articles", response_model=list[EditorialArticleOut])
async def list_all(
    db: DB,
    status: Annotated[str | None, Query(pattern=r"^(draft|review|published|archived)$")] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10_000),
):
    query = select(Article)
    if status:
        query = query.where(Article.status == status)
    rows = await db.scalars(query.order_by(Article.updated_at.desc(), Article.id.desc()).limit(limit).offset(offset))
    return rows.all()


@router.get("/articles/{article_id}", response_model=EditorialArticleOut)
async def get_one(article_id: int, db: DB):
    return await _get(db, article_id)


@router.post("/articles", response_model=EditorialArticleOut, status_code=201)
async def create(payload: ArticleWrite, db: DB, actor: Actor):
    data = payload.model_dump(mode="json")
    article = Article(**data, status="draft")
    db.add(article)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Ya existe un artículo con ese slug") from None
    _audit(db, actor, "create", article)
    await _commit(db)
    await db.refresh(article)
    return article


@router.patch("/articles/{article_id}", response_model=EditorialArticleOut)
async def update(article_id: int, payload: ArticleUpdate, db: DB, actor: Actor):
    article = await _get(db, article_id)
    changes = payload.model_dump(mode="json", exclude_unset=True, exclude_none=True)
    if article.published_at is not None and "slug" in changes and changes["slug"] != article.slug:
        # Cambiar la URL pública requiere redirecciones 301 (pendiente).
        raise HTTPException(409, "No se puede cambiar el slug de un artículo publicado")
    for key, value in changes.items():
        setattr(article, key, value)
    article.updated_at = utcnow()
    _audit(db, actor, "update", article, {"fields": sorted(changes)})
    await _commit(db)
    await db.refresh(article)
    return article


@router.post("/articles/{article_id}/status", response_model=EditorialArticleOut)
async def change_status(article_id: int, payload: StatusChange, db: DB, actor: Actor):
    article = await _get(db, article_id)
    target = payload.status
    if target not in TRANSITIONS[article.status]:
        raise HTTPException(409, f"Transición no permitida: {article.status} → {target}")
    if target == "published":
        problems = []
        if not article.sources:
            problems.append("añade al menos una fuente original")
        if len(article.body) < MIN_PUBLISH_BODY:
            problems.append(f"el cuerpo debe tener al menos {MIN_PUBLISH_BODY} caracteres")
        if problems:
            raise HTTPException(422, "No se puede publicar: " + "; ".join(problems))
        now = utcnow()
        article.reviewed_at = now
        article.reviewed_by = actor
        article.published_at = article.published_at or now
        from app.modules.articles.media import ensure_media
        await ensure_media(db,article)
    previous = article.status
    article.status = target
    article.updated_at = utcnow()
    _audit(db, actor, "status", article, {"from": previous, "to": target, "note": payload.note})
    await _commit(db)
    await db.refresh(article)
    return article
