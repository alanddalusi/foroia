"""Lectura pública del foro (solo temas aprobados)."""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import Category, Topic

router = APIRouter(tags=["forum"])
DB = Annotated[AsyncSession, Depends(get_db)]


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str
    description: str
    published_topics: int


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    title: str
    body: str
    author_name: str
    created_at: datetime


@router.get("/categories", response_model=list[CategoryOut])
async def categories(db: DB):
    counts = select(Topic.category_id, func.count(Topic.id).label('published_topics')).where(
        Topic.published.is_(True)).group_by(Topic.category_id).subquery()
    rows = (await db.execute(select(Category, func.coalesce(counts.c.published_topics, 0)).outerjoin(
        counts, Category.id == counts.c.category_id).order_by(Category.name))).all()
    return [CategoryOut(slug=row.slug, name=row.name, description=row.description, published_topics=count)
            for row, count in rows]


@router.get("/categories/{slug}/topics", response_model=list[TopicOut])
async def category_topics(slug: str, db: DB, limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0, le=50000)):
    category = await db.scalar(select(Category).where(Category.slug == slug))
    if category is None:
        raise HTTPException(404, "Categoría no encontrada")
    result = await db.scalars(
        select(Topic)
        .where(Topic.category_id == category.id, Topic.published.is_(True))
        .order_by(Topic.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.all()


@router.get("/topics/{slug}", response_model=TopicOut)
async def topic(slug: str, db: DB):
    result = await db.scalar(select(Topic).where(Topic.slug == slug, Topic.published.is_(True)))
    if result is None:
        raise HTTPException(404, "Tema no encontrado")
    return result


@router.get("/topics", response_model=list[TopicOut])
async def topics(db: DB, limit: int = Query(20, ge=1, le=50)):
    result = await db.scalars(
        select(Topic).where(Topic.published.is_(True)).order_by(Topic.created_at.desc()).limit(limit)
    )
    return result.all()
