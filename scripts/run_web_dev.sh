#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$ROOT/herminaCrawler-fe"

# Validasi backend
if [ ! -f "$ROOT/apps/api/main.py" ]; then
    echo "ERROR: FastAPI backend tidak ditemukan di apps/api/main.py"
    exit 1
fi

# Validasi frontend
if [ ! -f "$FRONTEND_DIR/package.json" ]; then
    echo "ERROR: Next.js frontend tidak ditemukan di herminaCrawler-fe/"
    exit 1
fi

echo ""
echo "🚀 Starting Hermina Review Intelligence..."
echo "   Backend : http://localhost:8000/api/docs"
echo "   Frontend: http://localhost:3000"
echo "   Tekan Ctrl+C untuk stop FE dan BE."
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "⏹  Stopping dev processes..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo "✅ Done."
}
trap cleanup EXIT INT TERM

# Start backend (activate venv)
cd "$ROOT"
source "$ROOT/venv/bin/activate"
PYTHONUNBUFFERED=1 python3 -m uvicorn apps.api.main:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend
cd "$FRONTEND_DIR"
npm run dev -- --hostname 127.0.0.1 --port 3000 &
FRONTEND_PID=$!

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
