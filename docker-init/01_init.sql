-- Initialize database extensions.
-- This file is executed by the official Postgres image against the database
-- specified by POSTGRES_DB (in docker-compose.yml that is `agentic_ai`).

-- Ensure extensions exist. Idempotent so it is safe to run multiple times.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Optional: set a default search_path or other DB-level settings here.
