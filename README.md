# ShopSide
Different places. One shopping trip.

Early implementation of a two-person shared shopping room. Fictional demo inventory; no purchases or AI responses are simulated.

## Run locally
Python 3.12 and Node 24 were used.

```sh
python3 -m venv .venv
.venv/bin/pip install -r services/api/requirements.lock
PYTHONPATH=services/api .venv/bin/uvicorn app.main:app --workers 1
# In another terminal:
cd apps/web
npm ci
npm run dev
```
Open the frontend on port 3000. Create a room, copy its invitation and open that invitation in a separate browser profile. Use distinct display names. The frontend proxies API requests to port 8000; HttpOnly membership cookies remain on the frontend origin.

`SHOPSIDE_DB` selects the SQLite path (default `/tmp/shopside.sqlite3`; set a persistent path for durable use). Run exactly one API process. No deployment has been performed.

## Implementation status
- Implemented: two-member invitations, opaque membership cookies, catalog, persisted spotlight, reactions, shortlist and shared chat; revision conflicts and command deduplication.
- Initial UI: responsive editorial layout and clearly labelled fictional products, using typographic illustrations rather than photography.
- Synchronization currently polls every 1.2 seconds. Presence is not tracked; participant names indicate membership.
- Not yet implemented: WebSockets, Alembic/SQLAlchemy migration, comparison, preferences, agent, cart, PayPal, checkout, Docker and browser journey verification.
- This is an initial increment, not the complete build brief or a release-ready app.

## Checks
```sh
PYTHONPATH=services/api .venv/bin/pytest services/api/tests -q
cd apps/web && npm run build
```
The API test exercises two independent cookie clients, unauthorized access, room capacity, shared spotlight/reaction, command deduplication and stale revision rejection. Browser-context and visual checks remain outstanding.
