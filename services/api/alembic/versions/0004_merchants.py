"""Persist sandbox merchant tenants and consented deal workflows."""
from alembic import op
revision='0004'
down_revision='0003'
branch_labels=None
depends_on=None

def upgrade():
    op.execute('CREATE TABLE IF NOT EXISTS merchants(id TEXT PRIMARY KEY, state TEXT NOT NULL)')
    op.execute('CREATE TABLE IF NOT EXISTS merchant_users(token_hash TEXT PRIMARY KEY, merchant_id TEXT NOT NULL, name TEXT NOT NULL)')
    op.execute('CREATE TABLE IF NOT EXISTS merchant_products(merchant_id TEXT NOT NULL, product_id TEXT NOT NULL, state TEXT NOT NULL, PRIMARY KEY(merchant_id,product_id))')
    op.execute('CREATE TABLE IF NOT EXISTS merchant_opportunities(id TEXT PRIMARY KEY, merchant_id TEXT NOT NULL, room_id TEXT NOT NULL, demand_key TEXT NOT NULL, state TEXT NOT NULL, UNIQUE(merchant_id,room_id,demand_key))')
    op.execute('CREATE TABLE IF NOT EXISTS merchant_jobs(id TEXT PRIMARY KEY, state TEXT NOT NULL)')

def downgrade():
    raise RuntimeError('Restore a database backup instead of dropping merchant data.')
