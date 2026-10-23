#!/usr/bin/env bash
# Start Saathi locally: backend on :8000 and frontend on :3000.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d backend/.venv ]; then
  echo "Creating backend venv..."
  python3 -m venv backend/.venv
  ( . backend/.venv/bin/activate && pip install -q -r backend/requirements.txt )
fi

if [ ! -d frontend/node_modules ]; then
  echo "Installing frontend deps..."
  ( cd frontend && npm install --no-audit --no-fund )
fi

echo "Applying migrations + seeding..."
( . backend/.venv/bin/activate && cd backend && alembic upgrade head && python seed.py )

echo "Starting backend on :8000 ..."
( . backend/.venv/bin/activate && cd backend && uvicorn app.main:app --port 8000 --reload ) &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null || true' EXIT

echo "Starting frontend on :3000 ..."
cd frontend && npm run dev
