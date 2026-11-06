"""Persist merchant inventory per exact variant."""
from alembic import op
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None
def upgrade():
    op.execute('CREATE TABLE IF NOT EXISTS inventory(product TEXT, variant TEXT, stock INTEGER NOT NULL CHECK(stock>=0), PRIMARY KEY(product,variant))')
def downgrade():
    raise RuntimeError('Restore a database backup instead of dropping inventory.')
