#!/usr/bin/env bash
set -euo pipefail

# Run all dependencies (Postgres) and start the application.
# Usage: ./scripts/run_all.sh [--no-seed] [--no-server]

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Load .env if present
if [ -f .env ]; then
  # shellcheck disable=SC1091
  source .env
fi

# Activate venv if present
if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Defaults
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-postgres}
DB_NAME=${DB_NAME:-agentic_ai}
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}

export DATABASE_URL=${DATABASE_URL:-postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}}

NO_SEED=0
NO_SERVER=0
for arg in "$@"; do
  case "$arg" in
    --no-seed) NO_SEED=1 ;;
    --no-server) NO_SERVER=1 ;;
  esac
done

echo "Starting dependencies with docker-compose..."
docker-compose up -d

# Wait for Postgres container to accept connections
echo "Waiting for Postgres to be ready..."
# Try docker-compose exec first; fallback to pg_isready locally
if docker-compose ps >/dev/null 2>&1; then
  for i in {1..60}; do
    if docker-compose exec -T db pg_isready -U "${DB_USER}" >/dev/null 2>&1; then
      echo "Postgres is ready (container)."
      break
    fi
    echo -n '.'; sleep 1
  done
else
  for i in {1..60}; do
    if pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" >/dev/null 2>&1; then
      echo "Postgres is ready (host)."
      break
    fi
    echo -n '.'; sleep 1
  done
fi

# Apply migrations
echo "Applying DB migrations (alembic)..."
python scripts/run_alembic.py upgrade head

# Seed sample properties unless disabled
if [ "$NO_SEED" -eq 0 ]; then
  echo "Seeding sample properties (scripts/seed_properties.py)..."
  python scripts/seed_properties.py || echo "Seeding failed (continuing)"
fi

# Start server unless disabled
if [ "$NO_SERVER" -eq 0 ]; then
  echo "Starting FastAPI server (uvicorn)..."
  chmod +x scripts/run_server.sh || true
  # Run in background with nohup so the script can finish
  nohup ./scripts/run_server.sh > run_server.log 2>&1 &
  echo "Server started (logs -> run_server.log)."
fi

echo "All done. Open http://localhost:8000/dashboard or http://localhost:8000/docs"
