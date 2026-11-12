"""Persistent editorial queue, bounded document cache and reported token usage."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0006_editorial_queue'
down_revision = '0005_analytics'
branch_labels = depends_on = None
J = sa.JSON().with_variant(postgresql.JSONB(), 'postgresql')


def upgrade():
    op.create_table('editorial_candidates',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('fingerprint', sa.String(64), nullable=False, unique=True),
        sa.Column('engine', sa.String(12), nullable=False), sa.Column('kind', sa.String(20), nullable=False),
        sa.Column('topic', sa.String(200), nullable=False), sa.Column('section', sa.String(30), nullable=False),
        sa.Column('intent', sa.String(300), nullable=False), sa.Column('keyword', sa.String(150), nullable=False),
        sa.Column('priority', sa.Integer, nullable=False), sa.Column('state', sa.String(24), nullable=False),
        sa.Column('reason', sa.String(80), nullable=False), sa.Column('attempts', sa.Integer, nullable=False),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True)),
        sa.Column('article_id', sa.Integer, sa.ForeignKey('articles.id')),
        sa.Column('target_article_id', sa.Integer, sa.ForeignKey('articles.id')),
        sa.Column('published_at', sa.DateTime(timezone=True)),
        sa.Column('details', J, nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("engine IN ('news','evergreen')", name='ck_editorial_engine'),
        sa.CheckConstraint("state IN ('queued','preparing','ready','generating','published','rejected','deferred','needs_verification')", name='ck_editorial_state'))
    op.create_index('ix_editorial_queue','editorial_candidates',['state','priority','next_attempt_at'])
    op.create_table('source_cache',sa.Column('url',sa.String(2000),primary_key=True),
        sa.Column('content_sha256',sa.String(64),nullable=False),sa.Column('document',J,nullable=False),
        sa.Column('fetched_at',sa.DateTime(timezone=True),nullable=False),sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_source_cache_expires_at','source_cache',['expires_at'])
    op.create_table('generation_usage',sa.Column('id',sa.Integer,primary_key=True),
        sa.Column('run_id',sa.Integer,sa.ForeignKey('research_runs.id'),nullable=False),
        sa.Column('candidate_id',sa.Integer,sa.ForeignKey('editorial_candidates.id')),
        sa.Column('model',sa.String(40),nullable=False),sa.Column('stage',sa.String(24),nullable=False),
        sa.Column('input_tokens',sa.Integer,nullable=False),sa.Column('output_tokens',sa.Integer,nullable=False),
        sa.Column('cached_tokens',sa.Integer,nullable=False),sa.Column('estimated_microusd',sa.Integer,nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_generation_usage_run_id','generation_usage',['run_id'])


def downgrade():
    op.drop_table('generation_usage'); op.drop_table('source_cache'); op.drop_table('editorial_candidates')
