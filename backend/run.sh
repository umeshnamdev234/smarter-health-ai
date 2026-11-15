#!/bin/bash
# Starts the Smarter Health AI API at http://localhost:8000 (docs: /docs)
set -e
cd "$(dirname "$0")"
[ -d .venv ] || uv venv --python 3.11 .venv
uv pip install -q --python .venv/bin/python -r requirements.txt
[ -f .env ] || cp .env.example .env

# Model server
curl -s http://localhost:11434/api/version >/dev/null || brew services start ollama

# PostgreSQL tunnel (minikube) — started once, keeps running in the background
if ! lsof -nP -iTCP:15432 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Starting PostgreSQL tunnel on localhost:15432 (log: .tunnel.log)"
  nohup ./scripts/db-tunnel.sh > .tunnel.log 2>&1 &
  sleep 2
fi

# Database migrations (Alembic)
.venv/bin/alembic upgrade head

exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
