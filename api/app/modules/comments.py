"""Comentarios de texto plano: todas las altas y ediciones requieren moderación."""
import base64
import hashlib
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.limits import client_address, limit
from app.models import Article, AuditLog, Comment, User, utcnow
from app.modules.accounts import current_user, csrf, roles

router = APIRouter(tags=["comments"])
DB = Annotated[AsyncSession, Depends(get_db)]
Member = Annotated[User, Depends(current_user)]
Moderator = Annotated[User, Depends(roles("moderator", "admin"))]


class CommentWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: str = Field(min_length=1, max_length=5000)

    @field_validator("body")
    @classmethod
    def clean(cls, value):
        value = value.strip()
        if not value or any(ord(c) < 32 and c not in "\n\t" for c in value):
            raise ValueError("Comentario no válido")
        return value


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["approved", "rejected", "removed"]
    version: str = Field(pattern=r"^[a-f0-9]{64}$")


def version_of(comment):
    from app.modules.accounts import aware
    value = f"{comment.id}|{comment.status}|{aware(comment.updated_at).isoformat()}|{comment.body}"
    return hashlib.sha256(value.encode()).hexdigest()


async def published_article(db, slug, lock=False):
    query = select(Article).where(Article.slug == slug, Article.status == "published")
    if lock:
        query = query.with_for_update()
    article = await db.scalar(query)
    if not article:
        raise HTTPException(404, "Artículo no encontrado")
    return article


def item(comment, author, slug=None, private=False):
    data = {"id": comment.id, "body": comment.body, "author_name": author,
            "created_at": comment.created_at, "updated_at": comment.updated_at}
    if private:
        data |= {"status": comment.status, "article_slug": slug, "user_id": comment.user_id, "version": version_of(comment)}
    return data


def after(query, cursor):
    if cursor:
        try:
            decoded = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
            date, cid = decoded.split("|")
            date, cid = datetime.fromisoformat(date), int(cid)
            if date.tzinfo is None or cid < 1 or cid > 2**63 - 1:
                raise ValueError()
        except (ValueError, UnicodeError):
            raise HTTPException(422, "Cursor no válido") from None
        query = query.where(or_(Comment.created_at < date, and_(Comment.created_at == date, Comment.id < cid)))
    return query


def next_cursor(rows, maximum):
    if len(rows) <= maximum:
        return None
    last = rows[maximum - 1][0]
    date = last.created_at
    from app.modules.accounts import aware
    return base64.urlsafe_b64encode(f"{aware(date).isoformat()}|{last.id}".encode()).decode().rstrip("=")


def audit(db, user, comment, action):
    db.add(AuditLog(actor=f"user:{user.id}", action=action, entity_type="comment", entity_id=comment.id))


@router.get("/articles/{slug}/comments")
async def public_comments(slug: str, db: DB, limit_count: int = Query(20, alias="limit", ge=1, le=50), cursor: str | None = Query(None, max_length=160)):
    article = await published_article(db, slug)
    query = select(Comment, User.display_name).join(User, User.id == Comment.user_id).where(
        Comment.article_id == article.id, Comment.status == "approved", User.blocked.is_(False))
    rows = (await db.execute(after(query, cursor).order_by(Comment.created_at.desc(), Comment.id.desc()).limit(limit_count + 1))).all()
    return {"items": [item(c, name) for c, name in rows[:limit_count]], "next_cursor": next_cursor(rows, limit_count)}


@router.post("/articles/{slug}/comments", status_code=201, dependencies=[Depends(csrf)])
async def create_comment(slug: str, payload: CommentWrite, request: Request, db: DB, user: Member):
    if not user.verified:
        raise HTTPException(403, "Verifica tu correo antes de comentar")
    await limit("comments-user", str(user.id), 10, 300)
    await limit("comments-ip", client_address(request), 30, 300)
    article = await published_article(db, slug, lock=True)
    if not article.comments_enabled:
        raise HTTPException(403, "Los comentarios están cerrados")
    # Evitar repetir exactamente el último comentario del mismo autor en el artículo.
    previous = await db.scalar(select(Comment).where(Comment.user_id == user.id, Comment.article_id == article.id).order_by(Comment.id.desc()).limit(1))
    if previous and previous.body == payload.body and previous.status != "removed":
        raise HTTPException(409, "Ese comentario ya se ha enviado")
    comment = Comment(article_id=article.id, user_id=user.id, body=payload.body, status="pending")
    db.add(comment)
    await db.flush()
    audit(db, user, comment, "comment_create")
    await db.commit()
    return item(comment, user.display_name, article.slug, True)


@router.get("/auth/comments")
async def own_comments(db: DB, user: Member, cursor: str | None = Query(None, max_length=160)):
    query = select(Comment, Article.slug).join(Article, Article.id == Comment.article_id).where(Comment.user_id == user.id)
    rows = (await db.execute(after(query, cursor).order_by(Comment.created_at.desc(), Comment.id.desc()).limit(21))).all()
    return {"items": [item(c, user.display_name, slug, True) for c, slug in rows[:20]], "next_cursor": next_cursor(rows, 20)}


async def owned(db, cid, user):
    comment = await db.scalar(select(Comment).where(Comment.id == cid).with_for_update())
    if not comment or comment.user_id != user.id:
        raise HTTPException(404, "Comentario no encontrado")
    return comment


@router.patch("/comments/{cid}", dependencies=[Depends(csrf)])
async def edit_comment(cid: int, payload: CommentWrite, db: DB, user: Member):
    await limit("comments-edit", str(user.id), 20, 300)
    comment = await owned(db, cid, user)
    article = await db.get(Article, comment.article_id)
    if not user.verified or not article or article.status != "published" or not article.comments_enabled or comment.status == "removed":
        raise HTTPException(403, "No se puede editar este comentario")
    comment.body, comment.status, comment.updated_at = payload.body, "pending", utcnow()
    audit(db, user, comment, "comment_edit")
    await db.commit()
    return item(comment, user.display_name, article.slug, True)


@router.delete("/comments/{cid}", dependencies=[Depends(csrf)])
async def remove_comment(cid: int, db: DB, user: Member):
    await limit("comments-remove", str(user.id), 20, 300)
    comment = await owned(db, cid, user)
    comment.status, comment.updated_at = "removed", utcnow()
    audit(db, user, comment, "comment_remove")
    await db.commit()
    return {"message": "Comentario retirado"}


@router.get("/moderation/comments")
async def moderation_queue(db: DB, user: Moderator, cursor: str | None = Query(None, max_length=160)):
    query = select(Comment, User.display_name, Article.slug).join(User, User.id == Comment.user_id).join(Article, Article.id == Comment.article_id).where(Comment.status == "pending")
    rows = (await db.execute(after(query, cursor).order_by(Comment.created_at.desc(), Comment.id.desc()).limit(21))).all()
    return {"items": [item(c, name, slug, True) for c, name, slug in rows[:20]], "next_cursor": next_cursor(rows, 20)}


@router.post("/moderation/comments/{cid}", dependencies=[Depends(csrf)])
async def moderate(cid: int, payload: Decision, db: DB, user: Moderator):
    await limit("moderation", str(user.id), 120, 300)
    comment = await db.scalar(select(Comment).where(Comment.id == cid).with_for_update())
    if not comment:
        raise HTTPException(404, "Comentario no encontrado")
    if payload.version != version_of(comment):
        raise HTTPException(409, "El comentario ha cambiado. Recarga la cola y revisa su nueva versión.")
    article = await db.get(Article, comment.article_id)
    author = await db.get(User, comment.user_id)
    if payload.status == "approved" and (not article or article.status != "published" or not author or author.blocked or comment.status == "removed"):
        raise HTTPException(409, "No se puede aprobar este comentario")
    comment.status, comment.updated_at = payload.status, utcnow()
    audit(db, user, comment, "comment_" + payload.status)
    await db.commit()
    return {"status": comment.status}
