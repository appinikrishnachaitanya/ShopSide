# Cloud Run + Cloud SQL PostgreSQL 17.11

## Frontend: runtime backend selection

Build `apps/web/Dockerfile` once. At runtime set `BACKEND_URL` to the API service's HTTP(S) origin (for example `https://your-api-...run.app`), without a path or trailing query. `API_INTERNAL_URL` remains supported as a fallback for existing deployments; `BACKEND_URL` wins. The Node server reads the variable when it starts and proxies `/api/*` HTTP requests and WebSocket upgrades, preserving the browser's frontend-origin membership cookies and Origin header. Changing the Cloud Run environment creates a new revision, but **does not require rebuilding the image**. The browser never needs the backend URL or database credentials.

For an IAM-protected Cloud Run API, set `BACKEND_ID_TOKEN_AUDIENCE` on the frontend to the API's service URL. Grant the frontend service account `roles/run.invoker` on the API; the proxy obtains and refreshes an ID token using its Cloud Run service identity for both HTTP and WebSocket calls. Omit this variable only when the API is configured to allow unauthenticated invocation. Never put a service-account JSON key in the image. The IAM-protected Cloud Run path requires a deployed verification; local tests cover the proxy without IAM.

## API and database

Build `services/Dockerfile` with `services/` as the build context. Use one worker and one instance: the application still keeps WebSocket subscribers, voice signaling, rate limits, and agent/payment locks in process memory. Set the API's maximum instances to one, route traffic to one revision, and avoid overlapping revisions while testing. Cloud Run can temporarily exceed scaling limits; this is **not** a guarantee of safe distributed operation. Multiple active API instances need shared signaling and locking before they are supported. Cloud Run WebSocket request timeouts can disconnect clients; use the existing reconnect control.

Attach the Cloud SQL PostgreSQL 17.11 instance to the API Cloud Run service, and grant its service identity the `roles/cloudsql.client` permission. Store `DATABASE_URL` in Secret Manager and inject it only into the API service. For a Cloud SQL Unix socket, its form is:

```
postgresql+psycopg://DB_USER:URL_ENCODED_PASSWORD@/DB_NAME?host=/cloudsql/PROJECT_ID:REGION:INSTANCE_ID
```

Use the Cloud SQL instance connection name exactly as provided by GCP; URL-encode special characters in usernames/passwords. Alternatively use a supported private-IP PostgreSQL connection and required VPC connectivity. `postgresql://` and `postgres://` URLs are also accepted and use psycopg 3. Keep credentials out of source control and logs. `DATABASE_URL` takes precedence over `SHOPSIDE_DB`; without it local SQLite remains available. Do not fall back to SQLite in Cloud Run when PostgreSQL is unavailable.

Set `WEB_ORIGIN` on the API to the exact public frontend origin (e.g. `https://shop.example.com`) and `COOKIE_SECURE=true`. Set the existing `PAYPAL_*`, `CHANNEL3_API_KEY`, `GEMINI_MODEL`, and Vertex AI authentication settings on the API according to ENVIRONMENT.md. The PayPal integration remains sandbox-only. Configure `WEBRTC_ICE_SERVERS` with a suitable TURN relay if voice is required.

Run the Alembic migration once as a controlled Cloud Run Job using the same image, Cloud SQL attachment, service identity and `DATABASE_URL`, with command:

```
alembic -c /app/alembic.ini upgrade head
```

The API currently creates missing baseline tables and seeds inventory at startup for compatibility; migrations should still be run explicitly. Avoid racing migrations and traffic.

## Moving an existing SQLite database

Back up the SQLite file and Cloud SQL database, stop all application traffic, and run Alembic against a **new empty** PostgreSQL database. Before starting the API (which seeds inventory), run the importer from a trusted machine that has connectivity to both databases:

```
DATABASE_URL="$DATABASE_URL" PYTHONPATH=services/api python scripts/import_sqlite_to_postgres.py /path/to/shopside.sqlite3
```

The importer reads a consistent, read-only SQLite snapshot and copies rooms, memberships, payments and inventory in one destination transaction. It refuses a nonempty destination and does not delete or modify the source. Verify data counts and application behavior before switching traffic. `alembic_version` is managed by the destination migration, not copied.

## Verification and known limits

PostgreSQL 17.11: Alembic upgrade and 15 backend tests passed, including reconnection after a terminated PostgreSQL connection against a local PostgreSQL container. The production frontend's HTTP proxy forwarded cookies/query strings to two different runtime backend URLs from the same build; a two-browser room journey also passed through the runtime proxy with PostgreSQL 17.11, including WebSockets and quote/cancel. Cloud SQL itself, Cloud Run IAM, live sandbox capture and cross-network voice were not deployed or verified in this workspace.

To repeat the backend tests against a **disposable** PostgreSQL database, migrate it first and set `SHOPSIDE_TEST_DATABASE_URL` (not `DATABASE_URL`) before running `PYTHONPATH=services/api pytest services/api/tests`. The test suite deliberately ignores an ambient `DATABASE_URL` to avoid modifying a deployment database. The verification test creates rooms, inventory reservations, and sandbox payment records; never point it at production.
