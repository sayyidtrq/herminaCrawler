#!/bin/sh
set -e

echo "[entrypoint] Running alembic migrations..."
python -m alembic upgrade head

echo "[entrypoint] Starting API server..."
exec python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
