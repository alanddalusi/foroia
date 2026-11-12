"""Manual executions separate from daily budget/history."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision='0007_editorial_executions'
down_revision='0006_editorial_queue'
branch_labels=depends_on=None

def upgrade():
    op.add_column('generation_usage',sa.Column('request_key',sa.String(64),nullable=True))
    op.create_index('ix_generation_usage_request_key','generation_usage',['request_key'],unique=True)
    op.create_table('editorial_executions',sa.Column('id',sa.Integer,primary_key=True),
        sa.Column('request_key',sa.String(64),nullable=False,unique=True),sa.Column('mode',sa.String(12),nullable=False),
        sa.Column('candidate_id',sa.Integer,sa.ForeignKey('editorial_candidates.id')),sa.Column('run_id',sa.Integer,sa.ForeignKey('research_runs.id')),
        sa.Column('article_id',sa.Integer,sa.ForeignKey('articles.id')),sa.Column('state',sa.String(24),nullable=False),
        sa.Column('reason',sa.String(80),nullable=False),sa.Column('status',sa.String(24),nullable=False),
        sa.Column('report',sa.JSON().with_variant(postgresql.JSONB(),'postgresql'),nullable=False),
        sa.Column('prepared',sa.JSON().with_variant(postgresql.JSONB(),'postgresql'),nullable=False),
        sa.Column('max_reserved_microusd',sa.Integer,nullable=False),sa.Column('reserved_microusd',sa.Integer,nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('expires_at',sa.DateTime(timezone=True)),sa.Column('started_at',sa.DateTime(timezone=True)),sa.Column('finished_at',sa.DateTime(timezone=True)),
        sa.CheckConstraint("state IN ('preparing','awaiting_approval','queued','running','completed','failed','uncertain','expired')",name='ck_execution_state'))
    op.create_index('ix_execution_queue','editorial_executions',['state','created_at'])

def downgrade():
    op.drop_table('editorial_executions')
    op.drop_index('ix_generation_usage_request_key',table_name='generation_usage')
    op.drop_column('generation_usage','request_key')
