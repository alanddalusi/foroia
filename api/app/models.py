"""Modelos ORM. El esquema real se gestiona con migraciones Alembic."""
from datetime import UTC, date, datetime

from sqlalchemy import JSON, BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, LargeBinary
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


class DailyPageView(Base):
    __tablename__ = "daily_page_views"
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    path: Mapped[str] = mapped_column(String(220), primary_key=True)
    views: Mapped[int] = mapped_column(BigInteger, default=0)

SECTIONS: dict[str, dict[str, str]] = {
    "actualidad": {"name": "Actualidad", "description": "Novedades de inteligencia artificial contrastadas con sus fuentes originales."},
    "herramientas": {"name": "Herramientas", "description": "Análisis prácticos de herramientas y servicios de IA, con sus límites."},
    "programacion": {"name": "Programación", "description": "Python, APIs, agentes y modelos locales con ejemplos comprobados."},
    "tutoriales": {"name": "Tutoriales", "description": "Guías paso a paso para aprender y aplicar la inteligencia artificial."},
}
ARTICLE_STATUSES = ("draft", "review", "published", "archived")


def utcnow() -> datetime:
    return datetime.now(UTC)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text)


class Topic(Base):
    __tablename__ = "topics"
    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True)
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    author_name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # Solo los temas aprobados se muestran públicamente.
    published: Mapped[bool] = mapped_column(Boolean, default=False)


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        CheckConstraint("status IN ('draft','review','published','archived')", name="ck_articles_status"),
        CheckConstraint("section IN ('actualidad','herramientas','programacion','tutoriales')", name="ck_articles_section"),
        Index("ix_articles_status_published_at", "status", "published_at"),
        Index("ix_articles_section_status_published_at", "section", "status", "published_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True)
    title: Mapped[str] = mapped_column(String(180))
    summary: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    section: Mapped[str] = mapped_column(String(30))
    author_name: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    # Lista de {"title", "url", "language"}; validada por Pydantic al escribir.
    sources: Mapped[list] = mapped_column(JSONType, default=list)
    media: Mapped[dict] = mapped_column(JSONType, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    comments_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


BigId = BigInteger().with_variant(Integer(), "sqlite")


class ArticleAsset(Base):
    __tablename__ = 'article_assets'
    key: Mapped[str] = mapped_column(String(90), primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey('articles.id'), index=True)
    content_type: Mapped[str] = mapped_column(String(30))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    sha256: Mapped[str] = mapped_column(String(64))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_entity", "entity_type", "entity_id"),)
    id: Mapped[int] = mapped_column(BigId, primary_key=True)
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(50))
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[int] = mapped_column(Integer)
    details: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('member','moderator','editor','admin')", name="ck_users_role"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="member")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserSession(Base):
    __tablename__ = "user_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AccountToken(Base):
    __tablename__ = "account_tokens"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(12))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class MailOutbox(Base):
    __tablename__ = "mail_outbox"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(150))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        CheckConstraint("status IN ('pending','approved','rejected','removed')", name="ck_comments_status"),
        CheckConstraint("length(body) BETWEEN 1 AND 5000", name="ck_comments_body"),
        Index("ix_comments_article_status_created_id", "article_id", "status", "created_at", "id"),
        Index("ix_comments_author_created_id", "user_id", "created_at", "id"),
        Index("ix_comments_status_created_id", "status", "created_at", "id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ResearchRun(Base):
    __tablename__ = 'research_runs'
    __table_args__ = (Index('ix_research_runs_created_at', 'created_at'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    editorial_date: Mapped[date] = mapped_column(Date, unique=True)
    status: Mapped[str] = mapped_column(String(24), default='running')
    reason: Mapped[str] = mapped_column(String(80), default='')
    reserved_microusd: Mapped[int] = mapped_column(Integer, default=0)
    article_id: Mapped[int | None] = mapped_column(ForeignKey('articles.id'), nullable=True)
    report: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EditorialLaneRun(Base):
    """Two durable workspaces under one daily budget and scheduler."""
    __tablename__ = 'editorial_lane_runs'
    __table_args__ = (
        Index('uq_editorial_lane_day', 'run_id', 'engine', 'slot', unique=True),
        CheckConstraint("engine IN ('news','evergreen')", name='ck_lane_engine'),
        CheckConstraint('slot BETWEEN 1 AND 2', name='ck_lane_slot'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('research_runs.id'), index=True)
    engine: Mapped[str] = mapped_column(String(12))
    slot: Mapped[int] = mapped_column(Integer, default=1, server_default='1')
    status: Mapped[str] = mapped_column(String(24), default='queued')
    reason: Mapped[str] = mapped_column(String(80), default='')
    candidate_id: Mapped[int | None] = mapped_column(ForeignKey('editorial_candidates.id'))
    article_id: Mapped[int | None] = mapped_column(ForeignKey('articles.id'))
    report: Mapped[dict] = mapped_column(JSONType, default=dict)
    owner_hash: Mapped[str] = mapped_column(String(64), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ResearchControl(Base):
    __tablename__ = 'research_control'
    id: Mapped[int] = mapped_column(primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    rapid_enabled: Mapped[bool] = mapped_column(Boolean, default=False,server_default='false')


class EditorialCandidate(Base):
    __tablename__ = 'editorial_candidates'
    __table_args__ = (
        CheckConstraint("engine IN ('news','evergreen')", name='ck_editorial_engine'),
        CheckConstraint("state IN ('queued','preparing','ready','generating','published','rejected','deferred','needs_verification','correction_pending','budget_pending','publication_error','technical_error')", name='ck_editorial_state'),
        Index('ix_editorial_queue', 'state', 'priority', 'next_attempt_at'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    engine: Mapped[str] = mapped_column(String(12))
    kind: Mapped[str] = mapped_column(String(20))
    topic: Mapped[str] = mapped_column(String(200))
    section: Mapped[str] = mapped_column(String(30))
    intent: Mapped[str] = mapped_column(String(300))
    keyword: Mapped[str] = mapped_column(String(150))
    priority: Mapped[int] = mapped_column(Integer, default=50)
    state: Mapped[str] = mapped_column(String(24), default='queued')
    reason: Mapped[str] = mapped_column(String(80), default='')
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    article_id: Mapped[int | None] = mapped_column(ForeignKey('articles.id'), nullable=True)
    target_article_id: Mapped[int | None] = mapped_column(ForeignKey('articles.id'), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    details: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SourceCache(Base):
    __tablename__ = 'source_cache'
    url: Mapped[str] = mapped_column(String(2000), primary_key=True)
    content_sha256: Mapped[str] = mapped_column(String(64))
    document: Mapped[dict] = mapped_column(JSONType)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class GenerationUsage(Base):
    __tablename__ = 'generation_usage'
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('research_runs.id'), index=True)
    candidate_id: Mapped[int | None] = mapped_column(ForeignKey('editorial_candidates.id'), nullable=True)
    model: Mapped[str] = mapped_column(String(40))
    stage: Mapped[str] = mapped_column(String(24))
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_microusd: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    request_key: Mapped[str | None]=mapped_column(String(64),nullable=True,unique=True)


class EditorialExecution(Base):
    __tablename__='editorial_executions'
    __table_args__=(CheckConstraint("state IN ('preparing','awaiting_approval','queued','running','completed','failed','uncertain','expired')",name='ck_execution_state'),
        Index('ix_execution_queue','state','created_at'))
    id: Mapped[int]=mapped_column(primary_key=True)
    request_key: Mapped[str]=mapped_column(String(64),unique=True)
    mode: Mapped[str]=mapped_column(String(12))
    candidate_id: Mapped[int | None]=mapped_column(ForeignKey('editorial_candidates.id'),nullable=True)
    run_id: Mapped[int | None]=mapped_column(ForeignKey('research_runs.id'),nullable=True)
    article_id: Mapped[int | None]=mapped_column(ForeignKey('articles.id'),nullable=True)
    state: Mapped[str]=mapped_column(String(24),default='preparing')
    reason: Mapped[str]=mapped_column(String(80),default='')
    status: Mapped[str]=mapped_column(String(24),default='running')
    report: Mapped[dict]=mapped_column(JSONType,default=dict)
    prepared: Mapped[dict]=mapped_column(JSONType,default=dict)
    max_reserved_microusd: Mapped[int]=mapped_column(Integer,default=0)
    reserved_microusd: Mapped[int]=mapped_column(Integer,default=0)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)
    expires_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True),nullable=True)
    started_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True),nullable=True)
    finished_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True),nullable=True)


class NewsScan(Base):
    __tablename__='news_scans'
    id: Mapped[int]=mapped_column(primary_key=True)
    window: Mapped[datetime]=mapped_column(DateTime(timezone=True),unique=True)
    state: Mapped[str]=mapped_column(String(20),default='running')
    report: Mapped[dict]=mapped_column(JSONType,default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    finished_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True),nullable=True)


class NewsFeedState(Base):
    __tablename__='news_feed_states'
    url: Mapped[str]=mapped_column(String(500),primary_key=True)
    failures: Mapped[int]=mapped_column(Integer,default=0)
    checked_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True),nullable=True)
    retry_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True),nullable=True)
    reason: Mapped[str]=mapped_column(String(80),default='')


class NewsObservation(Base):
    __tablename__='news_observations'
    key: Mapped[str]=mapped_column(String(64),primary_key=True)
    url: Mapped[str]=mapped_column(String(2000))
    feed_url: Mapped[str]=mapped_column(String(500))
    published_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True),nullable=True)
    candidate_id: Mapped[int | None]=mapped_column(ForeignKey('editorial_candidates.id'),nullable=True,index=True)
    state: Mapped[str]=mapped_column(String(20),default='pending',index=True)
    reason: Mapped[str]=mapped_column(String(80),default='')
    attempts: Mapped[int]=mapped_column(Integer,default=0)
    retry_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True),nullable=True)
    data: Mapped[dict]=mapped_column(JSONType,default=dict)
    first_seen_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
