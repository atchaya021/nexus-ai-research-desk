#!/usr/bin/env bash
# NEXUS — one-command dev startup (macOS / Linux).
#
# Starts the FastAPI backend (port 8000) and the Vite React frontend
# (port 5173) together, and stops both cleanly on Ctrl+C.
#
# Usage:
#   chmod +x start.sh   (first time only)
#   ./start.sh

set -e
cd "$(dirname "$0")"

echo "== NEXUS startup =="

# ---------------------------------------------------------------- backend --
if [ ! -d ".venv" ]; then
  echo "[backend] creating virtual environment (.venv)..."
  python3 -m venv .venv
fi

echo "[backend] installing/checking Python dependencies..."
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

echo "[backend] starting FastAPI on http://127.0.0.1:8000 ..."
.venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

cleanup() {
  echo ""
  echo "== stopping NEXUS =="
  kill "$BACKEND_PID" 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM

# Give the backend a moment to come up before the frontend proxies to it.
sleep 2

# --------------------------------------------------------------- frontend --
cd nexus-frontend

if [ ! -d "node_modules" ]; then
  echo "[frontend] installing npm dependencies (first run only, ~1 min)..."
  npm install
fi

echo "[frontend] starting Vite on http://127.0.0.1:5173 ..."
echo ""
echo "Open http://127.0.0.1:5173 in your browser once it says 'ready'."
echo "Press Ctrl+C here to stop both servers."
echo ""

npm run dev -- --host 127.0.0.1 --port 5173

cleanup
