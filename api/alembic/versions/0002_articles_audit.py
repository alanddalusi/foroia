"""Artículos del blog y registro de auditoría.

Revision ID: 0002_articles_audit
Revises: 0001_initial_forum
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_articles_audit"
down_revision = "0001_initial_forum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer, sa.Identity(always=False), primary_key=True),
        sa.Column("slug", sa.String(180), nullable=False, unique=True),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("summary", sa.String(300), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("section", sa.String(30), nullable=False),
        sa.Column("author_name", sa.String(80), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("sources", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(80), nullable=True),
        sa.CheckConstraint("status IN ('draft','review','published','archived')", name="ck_articles_status"),
        sa.CheckConstraint(
            "section IN ('actualidad','herramientas','programacion','tutoriales')", name="ck_articles_section"
        ),
        sa.CheckConstraint("status <> 'published' OR published_at IS NOT NULL", name="ck_articles_published_at"),
    )
    op.create_index("ix_articles_status_published_at", "articles", ["status", "published_at"])
    op.create_index("ix_articles_section_status_published_at", "articles", ["section", "status", "published_at"])
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger, sa.Identity(always=False), primary_key=True),
        sa.Column("actor", sa.String(80), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("entity_id", sa.Integer, nullable=False),
        sa.Column("details", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("articles")
