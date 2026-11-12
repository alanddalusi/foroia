"""Durable free news observation, sharing the editorial queue and budget."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision='0008_rapid_news'
down_revision='0007_editorial_executions'
branch_labels=depends_on=None
JSON=sa.JSON().with_variant(postgresql.JSONB(),'postgresql')

def upgrade():
    op.add_column('research_control',sa.Column('rapid_enabled',sa.Boolean(),nullable=False,server_default=sa.false()))
    op.create_table('news_scans',sa.Column('id',sa.Integer,primary_key=True),sa.Column('window',sa.DateTime(timezone=True),nullable=False,unique=True),
        sa.Column('state',sa.String(20),nullable=False),sa.Column('report',JSON,nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('finished_at',sa.DateTime(timezone=True)))
    op.create_table('news_feed_states',sa.Column('url',sa.String(500),primary_key=True),sa.Column('failures',sa.Integer,nullable=False),
        sa.Column('checked_at',sa.DateTime(timezone=True)),sa.Column('retry_at',sa.DateTime(timezone=True)),sa.Column('reason',sa.String(80),nullable=False))
    op.create_table('news_observations',sa.Column('key',sa.String(64),primary_key=True),sa.Column('url',sa.String(2000),nullable=False),
        sa.Column('feed_url',sa.String(500),nullable=False),sa.Column('published_at',sa.DateTime(timezone=True)),
        sa.Column('candidate_id',sa.Integer,sa.ForeignKey('editorial_candidates.id')),sa.Column('state',sa.String(20),nullable=False),
        sa.Column('reason',sa.String(80),nullable=False),sa.Column('attempts',sa.Integer,nullable=False),sa.Column('retry_at',sa.DateTime(timezone=True)),
        sa.Column('data',JSON,nullable=False),sa.Column('first_seen_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_news_observations_candidate_id','news_observations',['candidate_id'])
    op.create_index('ix_news_observations_state','news_observations',['state'])

def downgrade():
    op.drop_table('news_observations');op.drop_table('news_feed_states');op.drop_table('news_scans')
    op.drop_column('research_control','rapid_enabled')
