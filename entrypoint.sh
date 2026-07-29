#!/bin/sh
set -e

if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
  echo "[entrypoint] Running alembic migrations..."
  python -m alembic upgrade head
fi

if [ "$#" -gt 0 ]; then
  echo "[entrypoint] Starting custom process: $1"
  exec "$@"
fi

echo "[entrypoint] Starting API server..."
exec python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
