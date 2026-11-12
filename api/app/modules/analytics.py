"""Aggregate HTML requests. No IP, cookie, referrer or user agent is stored."""
import hmac
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.core.config import get_settings
from app.models import Article, DailyPageView, SECTIONS
from app.modules.articles.editorial import DB, require_editor

router = APIRouter()


def today():
    return datetime.now(ZoneInfo('Europe/Madrid')).date()


class PageHit(BaseModel):
    model_config = ConfigDict(extra='forbid')
    path: str = Field(max_length=220)


@router.post('/internal/page-view', status_code=204)
async def record(hit: PageHit, request: Request, db: DB):
    secret = get_settings().editorial_api_token
    if not secret or not hmac.compare_digest(secret.encode(), request.headers.get('x-internal-token', '').encode()):
        raise HTTPException(403, 'Acceso interno requerido')
    valid = hit.path == '/' or hit.path in {f'/{s}' for s in SECTIONS}
    if re.fullmatch(r'/articulos/[a-z0-9-]{1,180}', hit.path):
        valid = bool(await db.scalar(select(Article.id).where(
            Article.slug == hit.path.removeprefix('/articulos/'), Article.status == 'published')))
    if not valid:
        raise HTTPException(422, 'Ruta no medible')
    insert = pg_insert if db.bind.dialect.name == 'postgresql' else sqlite_insert
    statement = insert(DailyPageView).values(day=today(), path=hit.path, views=1)
    await db.execute(statement.on_conflict_do_update(
        index_elements=['day', 'path'], set_={'views': DailyPageView.views + 1}))
    await db.commit()
    return Response(status_code=204)


@router.get('/editorial/analytics', dependencies=[Depends(require_editor)])
async def dashboard(db: DB, days: Annotated[int, Query(ge=7, le=90)] = 30):
    end = today()
    start = end - timedelta(days=days - 1)
    previous = start - timedelta(days=days)
    rows = (await db.execute(select(DailyPageView.day, func.sum(DailyPageView.views))
        .where(DailyPageView.day >= previous, DailyPageView.day <= end)
        .group_by(DailyPageView.day))).all()
    counts = dict(rows)
    # Publication timestamps are converted to respect Madrid day boundaries.
    dates = (await db.scalars(select(Article.published_at).where(
        Article.published_at >= datetime.combine(start, datetime.min.time(), ZoneInfo('Europe/Madrid'))))).all()
    published_days = {}
    for stamp in dates:
        from datetime import UTC
        day = stamp.replace(tzinfo=stamp.tzinfo or UTC).astimezone(ZoneInfo('Europe/Madrid')).date()
        published_days[day] = published_days.get(day, 0) + 1
    series = [{'day': (d := start + timedelta(days=i)).isoformat(), 'views': counts.get(d, 0),
               'published': published_days.get(d, 0)} for i in range(days)]
    states = dict((await db.execute(select(Article.status, func.count()).group_by(Article.status))).all())
    top = (await db.execute(select(DailyPageView.path, func.sum(DailyPageView.views).label('total'), Article.title)
        .join(Article, DailyPageView.path == '/articulos/' + Article.slug)
        .where(DailyPageView.day >= start, DailyPageView.day <= end, Article.status == 'published')
        .group_by(DailyPageView.path, Article.title).order_by(func.sum(DailyPageView.views).desc(), DailyPageView.path).limit(10))).all()
    first = await db.scalar(select(func.min(DailyPageView.day)))
    return {'days': days, 'timezone': 'Europe/Madrid', 'first_recorded_day': first,
            'measurement':{'local_counter':'html_document_loads_not_unique_visitors',
                'ga4':{'status':'not_connected_to_dashboard','unique_users':None,'sessions':None,'countries':None,'organic_traffic':None,'landing_pages':None},
                'search_console':{'status':'property_metrics_not_connected','impressions':None,'clicks':None,'ctr':None,'average_position':None},
                'distinctions':'Las cargas HTML no son usuarios únicos; los clics de Search Console no son sesiones ni personas.'},
            'views': sum(r['views'] for r in series),
            'previous_views': sum(v for d, v in rows if previous <= d < start),
            'states': states, 'series': series,
            'top_articles': [{'path': path, 'title': title, 'views': n} for path, n, title in top]}
