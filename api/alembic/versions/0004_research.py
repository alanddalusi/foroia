"""Investigación nocturna: ejecución única diaria, presupuesto y pausa persistentes."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0004_research'
down_revision = '0003_accounts_comments'
branch_labels = depends_on = None


def upgrade():
    op.create_table('research_runs',
        sa.Column('id', sa.Integer, sa.Identity(), primary_key=True),
        sa.Column('editorial_date', sa.Date, nullable=False, unique=True),
        sa.Column('status', sa.String(24), nullable=False),
        sa.Column('reason', sa.String(80), nullable=False),
        sa.Column('reserved_microusd', sa.Integer, nullable=False),
        sa.Column('article_id', sa.Integer, sa.ForeignKey('articles.id'), nullable=True),
        sa.Column('report', JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_research_runs_created_at', 'research_runs', ['created_at'])
    op.create_table('research_control', sa.Column('id', sa.Integer, primary_key=True), sa.Column('enabled', sa.Boolean, nullable=False))
    op.execute(sa.text('INSERT INTO research_control (id, enabled) VALUES (1, true)'))


def downgrade():
    op.drop_table('research_control')
    op.drop_index('ix_research_runs_created_at', table_name='research_runs')
    op.drop_table('research_runs')
