"""Owned article illustrations and versioned, validated multimedia metadata."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision='0009_article_media'
down_revision='0008_rapid_news'
branch_labels=depends_on=None

def upgrade():
    op.add_column('articles',sa.Column('media',sa.JSON().with_variant(postgresql.JSONB(),'postgresql'),nullable=False,server_default=sa.text("'{}'")))
    op.create_table('article_assets',sa.Column('key',sa.String(90),primary_key=True),
        sa.Column('article_id',sa.Integer,sa.ForeignKey('articles.id'),nullable=False),
        sa.Column('content_type',sa.String(30),nullable=False),sa.Column('content',sa.LargeBinary,nullable=False),
        sa.Column('sha256',sa.String(64),nullable=False))
    op.create_index('ix_article_assets_article_id','article_assets',['article_id'])

def downgrade():
    op.drop_table('article_assets')
    op.drop_column('articles','media')
