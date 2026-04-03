#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/UTradeMi"
PY="$APP_DIR/.venv/bin/python"

cd "$APP_DIR"

git fetch --all
git reset --hard origin/main

if [ ! -d ".venv" ]; then
  python3.12 -m venv .venv
fi

"$PY" -m pip install -U pip
"$PY" -m pip install -r requirements.txt

# Kill previous instance
pkill -f "uvicorn app.main:app" || true

# Start FastAPI with uvicorn
nohup "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > log.txt 2>&1 &
echo "Started. Tail logs with: tail -n 200 -f $APP_DIR/log.txt"