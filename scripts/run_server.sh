#!/usr/bin/env bash
# Simple script to run the FastAPI app with Uvicorn
# Usage: ./scripts/run_server.sh
set -e

export DATABASE_URL=${DATABASE_URL:-postgresql+psycopg2://postgres:postgres@127.0.0.1:15432/agentic_ai}

# If inside Docker compose, prefer the container DB host 'db'
if [ "$DOCKER_COMPOSE" = "1" ]; then
  export DATABASE_URL="postgresql+psycopg2://postgres:postgres@db:5432/agentic_ai"
fi

# Run uvicorn (if inside container this will bind to 0.0.0.0:8000 and be reachable from host via compose mapping)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
