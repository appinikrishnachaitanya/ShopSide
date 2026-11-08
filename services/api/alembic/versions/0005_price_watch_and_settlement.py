"""Persist signed Channel3 events, shared watches, and PayPal settlement jobs."""
from alembic import op

revision='0005'
down_revision='0004'
branch_labels=None
depends_on=None


def upgrade():
    op.execute('CREATE TABLE IF NOT EXISTS paypal_webhook_payloads(id TEXT PRIMARY KEY, state TEXT NOT NULL)')
    op.execute('CREATE TABLE IF NOT EXISTS channel3_webhook_events(id TEXT PRIMARY KEY, event_type TEXT NOT NULL, received_at TEXT NOT NULL, state TEXT NOT NULL)')
    op.execute('CREATE TABLE IF NOT EXISTS channel3_watches(id TEXT PRIMARY KEY, room TEXT NOT NULL, participant TEXT NOT NULL, product_id TEXT NOT NULL, subscription_id TEXT NOT NULL, scope TEXT NOT NULL, threshold_cents INTEGER NOT NULL, status TEXT NOT NULL, state TEXT NOT NULL)')
    op.execute('CREATE INDEX IF NOT EXISTS channel3_watches_subscription_idx ON channel3_watches(subscription_id,status)')
    op.execute('CREATE INDEX IF NOT EXISTS channel3_watches_room_idx ON channel3_watches(room,participant)')
    op.execute('CREATE TABLE IF NOT EXISTS settlement_jobs(id TEXT PRIMARY KEY, payment_id TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL)')
    op.execute('CREATE INDEX IF NOT EXISTS settlement_jobs_status_idx ON settlement_jobs(status)')


def downgrade():
    raise RuntimeError('Restore a database backup instead of dropping watches or settlement history.')
