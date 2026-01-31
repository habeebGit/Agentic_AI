#!/usr/bin/env bash
# Simple script to run the FastAPI app with Uvicorn
# Usage: ./scripts/run_server.sh
set -e

export DATABASE_URL=${DATABASE_URL:-postgresql+psycopg2://postgres:postgres@localhost:5432/agentic_ai}

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
