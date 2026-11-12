"""Independent editorial workspaces; daily accounting remains on research_runs."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0010_editorial_lanes'
down_revision = '0009_article_media'
branch_labels = depends_on = None


def upgrade():
    op.create_table('editorial_lane_runs',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('run_id', sa.Integer, sa.ForeignKey('research_runs.id'), nullable=False),
        sa.Column('engine', sa.String(12), nullable=False),
        sa.Column('status', sa.String(24), nullable=False),
        sa.Column('reason', sa.String(80), nullable=False),
        sa.Column('candidate_id', sa.Integer, sa.ForeignKey('editorial_candidates.id')),
        sa.Column('article_id', sa.Integer, sa.ForeignKey('articles.id')),
        sa.Column('report', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=False),
        sa.Column('owner_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint("engine IN ('news','evergreen')", name='ck_lane_engine'))
    op.create_index('ix_editorial_lane_runs_run_id', 'editorial_lane_runs', ['run_id'])
    op.create_index('uq_editorial_lane_day', 'editorial_lane_runs', ['run_id', 'engine'], unique=True)


def downgrade():
    op.drop_table('editorial_lane_runs')
