# ShopSide
Different places. One shopping trip.

Early implementation of a two-person shared shopping room. Fictional demo inventory; no purchases or AI responses are simulated.

## Run locally
Python 3.12 and Node 24 were used.

```sh
python3 -m venv .venv
.venv/bin/pip install -r services/api/requirements.lock
 .venv/bin/alembic -c services/api/alembic.ini upgrade head
PYTHONPATH=services/api .venv/bin/uvicorn app.main:app --workers 1
# In another terminal:
cd apps/web
npm ci
npm run dev
```
Open the frontend on port 3000. Create a room, copy its invitation and open that invitation in a separate browser profile. Use distinct display names. The frontend proxies API requests to port 8000; HttpOnly membership cookies remain on the frontend origin.

`SHOPSIDE_DB` selects the SQLite path (default `/tmp/shopside.sqlite3`; set a persistent path for durable use). Run exactly one API process. No deployment has been performed.

## Implementation status
Implemented: invitations, opaque HttpOnly membership cookies, two-member capacity, persisted spotlight/reactions/shortlist/chat, WebSocket revision snapshots, explicit reconnect, search, two-product comparison, preferences, payer-confirmed budget, one-item standard-variant cart and agent cart proposals. The UI uses original MIT-licensed vector artwork for fictional products.

Gemini integration uses the Google Gen AI SDK and tools with a five-call automatic loop limit and request deadline. Set `GEMINI_API_KEY` and a model ID available to your account in `GEMINI_MODEL`. Tool activity is shared. Provider failures are explicit; there is no canned AI fallback.

Sandbox payment endpoints implement payer-only frozen quotes, durable operation/request IDs, create, capture, provider read-back, minimal shared status and payer-only capture receipt response. Set sandbox credentials from `.env.example`. Unknown provider outcomes require status checks. No live inference or real sandbox purchase has been verified yet.

Run exactly one API worker. SQLite JSON room records and process-local locks are an initial implementation; stronger stock accounting, crash/restart payment reconciliation coverage, signed webhooks, multi-item/quantity controls, richer variant data, full accessibility checks, photographic assets and release evidence remain unfinished. A quote can only be cancelled before provider creation; otherwise reconcile its status. No webhook endpoint is exposed.

Docker Compose is provided but has not been built here: copy `.env.example` to `.env`, enter credentials securely, and run `docker compose up --build`. Never commit `.env`.

## Checks
```sh
PYTHONPATH=services/api .venv/bin/pytest services/api/tests -q
cd apps/web && npm run build
```
The API test exercises two independent cookie clients, unauthorized access, room capacity, shared spotlight/reaction, command deduplication and stale revision rejection. Browser-context and visual checks remain outstanding.

See [verification](docs/VERIFICATION.md), [judge/demo guide](docs/DEMO.md), and [image provenance](fixtures/PROVENANCE.md). This remains a development build, not a completed release.
