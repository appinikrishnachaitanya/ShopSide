#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
.venv/bin/pip install -r services/api/requirements.lock
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi
export SHOPSIDE_DB="${SHOPSIDE_DB:-$PWD/shopside.sqlite3}"
.venv/bin/alembic -c services/api/alembic.ini upgrade head
(cd apps/web && npm ci)
PYTHONPATH=services/api .venv/bin/uvicorn app.main:app --host 0.0.0.0 --workers 1 &
api_pid=$!
trap 'kill "$api_pid" 2>/dev/null || true' EXIT INT TERM
(cd apps/web && npm run dev)
