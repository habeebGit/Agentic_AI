#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Checking Docker is running..."
if ! docker info >/dev/null 2>&1; then
  echo "Docker does not appear to be running. Start Docker Desktop and try again." >&2
  exit 1
fi

echo "==> Bringing down any existing containers and removing volumes (db data will be removed)..."
docker compose down -v || true

echo "==> Starting containers..."
docker compose up -d

echo "==> Waiting for Postgres service to become available (up to 60s)..."
ready=0
for i in {1..60}; do
  if docker compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done

if [ "$ready" -ne 1 ]; then
  echo "Postgres did not become ready in time. Check 'docker compose logs db' for details." >&2
  exit 1
fi

echo "==> Ensuring database 'agentic_ai' exists..."
EXISTS=$(docker compose exec -T db psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='agentic_ai';") || true
if [ "${EXISTS:-}" != "1" ]; then
  echo "Creating database agentic_ai..."
  docker compose exec -T db psql -U postgres -c "CREATE DATABASE agentic_ai;"
else
  echo "Database agentic_ai already exists, skipping creation."
fi

echo "==> Ensuring required extensions exist in agentic_ai..."
docker compose exec -T db psql -U postgres -d agentic_ai -c "CREATE EXTENSION IF NOT EXISTS pgcrypto; CREATE EXTENSION IF NOT EXISTS citext; CREATE EXTENSION IF NOT EXISTS pg_trgm; CREATE EXTENSION IF NOT EXISTS btree_gin;"

echo "==> Exporting DATABASE_URL for local tools (in this shell only)..."
export DATABASE_URL="postgresql+psycopg2://postgres:postgres@127.0.0.1:15432/agentic_ai"

echo "==> Running Alembic migrations..."
python3 scripts/run_alembic.py upgrade head

echo "==> Seeding sample data (if script exists)..."
if [ -f "scripts/seed_properties.py" ]; then
  python3 scripts/seed_properties.py || true
fi

echo "==> Setup complete. Start the server with: ./scripts/run_server.sh"
