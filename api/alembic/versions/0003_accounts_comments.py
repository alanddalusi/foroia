"""Cuentas, sesiones revocables, correo transaccional y comentarios moderados."""
import sqlalchemy as sa
from alembic import op

revision = "0003_accounts_comments"
down_revision = "0002_articles_audit"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users",
        sa.Column("id", sa.Integer, sa.Identity(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("verified", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("blocked", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('member','moderator','editor','admin')", name="ck_users_role"))
    op.create_table("user_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])
    op.create_table("account_tokens",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("purpose", sa.String(12), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_account_tokens_user_id", "account_tokens", ["user_id"])
    op.create_index("ix_account_tokens_expires_at", "account_tokens", ["expires_at"])
    op.create_table("mail_outbox",
        sa.Column("id", sa.Integer, sa.Identity(), primary_key=True),
        sa.Column("recipient", sa.String(254), nullable=False),
        sa.Column("subject", sa.String(150), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("sent_at", sa.DateTime(timezone=True)))
    op.create_table("comments",
        sa.Column("id", sa.Integer, sa.Identity(), primary_key=True),
        sa.Column("article_id", sa.Integer, sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('pending','approved','rejected','removed')", name="ck_comments_status"),
        sa.CheckConstraint("length(body) BETWEEN 1 AND 5000", name="ck_comments_body"))
    op.create_index("ix_comments_article_status_created_id", "comments", ["article_id", "status", "created_at", "id"])
    op.create_index("ix_comments_author_created_id", "comments", ["user_id", "created_at", "id"])
    op.create_index("ix_comments_status_created_id", "comments", ["status", "created_at", "id"])
    op.add_column("articles", sa.Column("comments_enabled", sa.Boolean, nullable=False, server_default=sa.true()))


def downgrade():
    op.drop_column("articles", "comments_enabled")
    for name in ("comments", "mail_outbox", "account_tokens", "user_sessions", "users"):
        op.drop_table(name)
