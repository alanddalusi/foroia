"""Daily aggregate counters without visitor identifiers."""
from alembic import op
import sqlalchemy as sa

revision = '0005_analytics'
down_revision = '0004_research'
branch_labels = depends_on = None


def upgrade():
    op.create_table('daily_page_views',
        sa.Column('day', sa.Date, primary_key=True),
        sa.Column('path', sa.String(220), primary_key=True),
        sa.Column('views', sa.BigInteger, nullable=False))


def downgrade():
    op.drop_table('daily_page_views')
