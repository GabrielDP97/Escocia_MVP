#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source .venv/bin/activate
python -m uvicorn backend.app:app --reload --port 8000 &
BACKEND_PID=$!
cd frontend
npm run dev
kill "$BACKEND_PID" 2>/dev/null || true
