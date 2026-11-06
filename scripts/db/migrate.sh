#!/usr/bin/env bash
# Apply or inspect Alembic migrations using the configured database.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="$repo_root/services/api${PYTHONPATH:+:$PYTHONPATH}"
if [[ -n "${ALEMBIC_BIN:-}" ]]; then
  alembic_bin="$ALEMBIC_BIN"
elif [[ -x "$repo_root/.venv/bin/alembic" ]]; then
  alembic_bin="$repo_root/.venv/bin/alembic"
else
  alembic_bin="alembic"
fi
case "${1:-upgrade}" in
  upgrade) exec "$alembic_bin" -c "$repo_root/services/api/alembic.ini" upgrade head ;;
  current) exec "$alembic_bin" -c "$repo_root/services/api/alembic.ini" current ;;
  *) printf 'Usage: %s [upgrade|current]\n' "$0" >&2; exit 2 ;;
esac
