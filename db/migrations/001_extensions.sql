-- 001_extensions.sql
-- Enable helpful Postgres extensions used by the schema
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS citext;     -- case-insensitive text
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- text search / similarity
CREATE EXTENSION IF NOT EXISTS btree_gin;  -- GIN support for btree indexes

-- NOTE: If you prefer uuid-ossp, add: CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
