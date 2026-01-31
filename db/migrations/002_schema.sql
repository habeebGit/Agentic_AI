-- 002_schema.sql
-- Core canonical schema for commercial property due-diligence

-- USERS / ROLES
CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email citext NOT NULL UNIQUE,
  full_name text,
  role text NOT NULL DEFAULT 'analyst', -- analyst | investor | admin
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- PROPERTIES (canonical)
CREATE TABLE IF NOT EXISTS properties (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text,
  property_type text NOT NULL,
  building_sqft numeric,
  lot_sqft numeric,
  year_built integer,
  stories integer,
  address_street text NOT NULL,
  address_city text NOT NULL,
  address_state text NOT NULL,
  address_zip text NOT NULL,
  address_country text NOT NULL DEFAULT 'US',
  lat double precision,
  lon double precision,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  last_synced_at timestamptz
);

-- SOURCE IDS (one property can have multiple source identifiers)
CREATE TABLE IF NOT EXISTS property_source_ids (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  provider text NOT NULL,
  provider_id text NOT NULL,
  raw_payload jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(property_id, provider, provider_id)
);

-- PROVENANCE ENTRIES
CREATE TABLE IF NOT EXISTS provenance_entries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  field_path text NOT NULL,
  provider text NOT NULL,
  raw_reference text,
  fetched_at timestamptz NOT NULL DEFAULT now(),
  confidence numeric NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  raw_value jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- FINANCIALS (last12mo and historical time series)
CREATE TABLE IF NOT EXISTS financials_last12mo (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  gross_income numeric,
  net_operating_income numeric,
  total_expenses numeric,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS financials_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  year integer NOT NULL,
  noi numeric,
  gross numeric,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- OCCUPANCY / LEASES
CREATE TABLE IF NOT EXISTS leases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  tenant_name text,
  leased_sqft numeric,
  lease_start date,
  lease_end date,
  rent_psf numeric,
  source text,
  raw_payload jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- DOCUMENTS (title reports, leases, inspections)
CREATE TABLE IF NOT EXISTS documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  name text NOT NULL,
  url text,
  mime_type text,
  uploaded_by uuid REFERENCES users(id),
  raw_metadata jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- COMPS
CREATE TABLE IF NOT EXISTS comps (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  provider text,
  sale_date date,
  sale_price numeric,
  distance_meters integer,
  similarity_score numeric,
  raw_payload jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- VALUATION MODELS (results and inputs)
CREATE TABLE IF NOT EXISTS valuation_models (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  model_name text NOT NULL,
  model_version text,
  inputs jsonb,
  outputs jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- RISK SCORES
CREATE TABLE IF NOT EXISTS risk_scores (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  title_risk numeric,
  flood_risk numeric,
  market_risk numeric,
  overall_confidence numeric CHECK (overall_confidence >= 0 AND overall_confidence <= 1),
  details jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- AGENT TASKS / LOGS
CREATE TABLE IF NOT EXISTS agent_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id text NOT NULL UNIQUE,
  agent_name text NOT NULL,
  property_id uuid REFERENCES properties(id) ON DELETE SET NULL,
  run_mode text,
  user_id uuid REFERENCES users(id),
  status text NOT NULL,
  log jsonb,
  report_id uuid REFERENCES documents(id), -- link to generated report document
  request_id text, -- idempotency key
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- REPORTS (structured report storage)
CREATE TABLE IF NOT EXISTS reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id uuid REFERENCES properties(id) ON DELETE SET NULL,
  report_id text NOT NULL UNIQUE,
  summary text,
  sections jsonb,
  confidence_overall numeric CHECK (confidence_overall >= 0 AND confidence_overall <= 1),
  generated_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- APPROVALS
CREATE TABLE IF NOT EXISTS approvals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  report_id uuid NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id),
  decision text NOT NULL,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- AUDIT LOG (generic immutable event log)
CREATE TABLE IF NOT EXISTS audit_logs (
  id bigserial PRIMARY KEY,
  event_time timestamptz NOT NULL DEFAULT now(),
  user_id uuid REFERENCES users(id),
  event_type text NOT NULL,
  payload jsonb
);
