"""Store illustrative relocation policies without touching existing rooms."""
from alembic import op
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None

def upgrade():
    op.execute('CREATE TABLE IF NOT EXISTS relocation_policies(id TEXT PRIMARY KEY, state TEXT NOT NULL)')

def downgrade():
    raise RuntimeError('Restore a database backup instead of dropping relocation policies.')
