"""Recovery states and a second practical slot, preserving existing data."""
from alembic import op
import sqlalchemy as sa

revision = '0011_recoverable_editorial'
down_revision = '0010_editorial_lanes'
branch_labels = depends_on = None
OLD = "state IN ('queued','preparing','ready','generating','published','rejected','deferred','needs_verification')"
NEW = OLD[:-1] + ",'correction_pending','budget_pending','publication_error','technical_error')"


def upgrade():
    with op.batch_alter_table('editorial_candidates') as b:
        b.drop_constraint('ck_editorial_state', type_='check')
        b.create_check_constraint('ck_editorial_state', NEW)
    with op.batch_alter_table('editorial_lane_runs') as b:
        b.add_column(sa.Column('slot', sa.Integer(), server_default='1', nullable=False))
        b.drop_index('uq_editorial_lane_day')
        b.create_index('uq_editorial_lane_day', ['run_id', 'engine', 'slot'], unique=True)
        b.create_check_constraint('ck_lane_slot', 'slot BETWEEN 1 AND 2')


def downgrade():
    # Refuse a lossy downgrade. Roll back the application with this additive
    # schema retained, rather than dropping a second slot and its audit trail.
    conn = op.get_bind()
    if conn.scalar(sa.text('SELECT count(*) FROM editorial_lane_runs WHERE slot != 1')):
        raise RuntimeError('Second-slot history exists; retain additive migration')
    conn.execute(sa.text("UPDATE editorial_candidates SET state='deferred' WHERE state IN ('correction_pending','budget_pending','publication_error','technical_error')"))
    with op.batch_alter_table('editorial_lane_runs') as b:
        b.drop_constraint('ck_lane_slot', type_='check')
        b.drop_index('uq_editorial_lane_day')
        b.drop_column('slot')
        b.create_index('uq_editorial_lane_day', ['run_id', 'engine'], unique=True)
    with op.batch_alter_table('editorial_candidates') as b:
        b.drop_constraint('ck_editorial_state', type_='check')
        b.create_check_constraint('ck_editorial_state', OLD)
