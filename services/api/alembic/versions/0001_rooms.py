"""Initial persisted rooms, memberships and payment operations."""
from alembic import op
revision='0001'
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
    op.execute('CREATE TABLE IF NOT EXISTS rooms(id TEXT PRIMARY KEY, invite TEXT UNIQUE, state TEXT)')
    op.execute('CREATE TABLE IF NOT EXISTS members(token TEXT PRIMARY KEY, room TEXT, name TEXT)')
    op.execute('CREATE TABLE IF NOT EXISTS payments(id TEXT PRIMARY KEY, room TEXT, state TEXT)')
def downgrade():
    raise RuntimeError('Destructive downgrade is intentionally unsupported; restore a database backup.')
