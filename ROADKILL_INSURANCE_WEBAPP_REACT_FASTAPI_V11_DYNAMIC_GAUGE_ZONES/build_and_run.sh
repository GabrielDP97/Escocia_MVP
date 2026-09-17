#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source .venv/bin/activate
cd frontend
npm run build
cd ..
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
