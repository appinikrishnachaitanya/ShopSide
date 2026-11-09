-- Read-only PostgreSQL/psql proof check. Supply the PayPal order ID:
-- psql "$DATABASE_URL" -v paypal_order_id='SANDBOX_ORDER_ID' -f scripts/db/verify_paypal_receipt.sql
-- Use a standard PostgreSQL connection URI, not SQLAlchemy's +psycopg URI.
BEGIN READ ONLY;
SELECT state::jsonb->>'id' AS shopside_payment_id,
       state::jsonb->>'provider_id' AS paypal_order_id,
       state::jsonb->>'capture' AS capture_id,
       state::jsonb->>'status' AS payment_status,
       state::jsonb->>'total' AS total_minor_units,
       state::jsonb->>'currency' AS currency,
       state::jsonb->>'verification' AS verification,
       state::jsonb->>'paid_at' AS paid_at
FROM payments
WHERE state::jsonb->>'provider_id' = :'paypal_order_id';
SELECT e.id AS event_id, e.event_type, e.received_at,
       p.state::jsonb->>'order_id' AS paypal_order_id,
       p.state::jsonb->>'capture_id' AS capture_id,
       p.state::jsonb->>'status' AS processing_status
FROM paypal_webhook_events e
JOIN paypal_webhook_payloads p ON p.id = e.id
WHERE p.state::jsonb->>'order_id' = :'paypal_order_id'
ORDER BY e.received_at;
COMMIT;
