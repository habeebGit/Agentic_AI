-- db/sqlalchemy/queries.sql
-- Parameterized SQL queries prepared for use with SQLAlchemy (text() or connection.execute)
-- Use named parameters (e.g. :id, :property_type) when binding.

-- 1) Insert a new property (simple)
-- Params: id, title, property_type, address_street, address_city, address_state, address_zip, address_country, building_sqft, lat, lon
INSERT INTO properties (
  id, title, property_type, address_street, address_city, address_state, address_zip, address_country,
  building_sqft, lat, lon, created_at, updated_at
) VALUES (
  COALESCE(:id::uuid, gen_random_uuid()), :title, :property_type, :address_street, :address_city, :address_state, :address_zip, COALESCE(:address_country,'US'),
  :building_sqft, :lat, :lon, now(), now()
)
RETURNING id;

-- 2) Upsert property by id (update on conflict)
-- Params: id, title, property_type, address_street, address_city, address_state, address_zip
INSERT INTO properties (id, title, property_type, address_street, address_city, address_state, address_zip, updated_at)
VALUES (:id::uuid, :title, :property_type, :address_street, :address_city, :address_state, :address_zip, now())
ON CONFLICT (id) DO UPDATE
  SET title = EXCLUDED.title,
      property_type = EXCLUDED.property_type,
      address_street = EXCLUDED.address_street,
      address_city = EXCLUDED.address_city,
      address_state = EXCLUDED.address_state,
      address_zip = EXCLUDED.address_zip,
      updated_at = now()
RETURNING id;

-- 3) Find property_id by source id
-- Params: provider, provider_id
SELECT property_id
FROM property_source_ids
WHERE provider = :provider AND provider_id = :provider_id
LIMIT 1;

-- 4) Insert property_source_id (attach a source identifier)
-- Params: property_id, provider, provider_id, raw_payload
INSERT INTO property_source_ids (property_id, provider, provider_id, raw_payload, created_at)
VALUES (:property_id::uuid, :provider, :provider_id, :raw_payload::jsonb, now())
ON CONFLICT (property_id, provider, provider_id) DO UPDATE
  SET raw_payload = COALESCE(property_source_ids.raw_payload, EXCLUDED.raw_payload)
RETURNING id;

-- 5) Insert a provenance entry
-- Params: property_id, field_path, provider, raw_reference, fetched_at, confidence, raw_value
INSERT INTO provenance_entries (property_id, field_path, provider, raw_reference, fetched_at, confidence, raw_value, created_at)
VALUES (:property_id::uuid, :field_path, :provider, :raw_reference, COALESCE(:fetched_at, now()), :confidence::numeric, :raw_value::jsonb, now())
RETURNING id;

-- 6) Get low-confidence fields for a property
-- Params: property_id, threshold
SELECT field_path, provider, raw_reference, fetched_at, confidence, raw_value
FROM provenance_entries
WHERE property_id = :property_id::uuid AND confidence < COALESCE(:threshold::numeric, 0.6)
ORDER BY fetched_at DESC;

-- 7) Insert / update last12mo financials
-- Params: property_id, gross_income, net_operating_income, total_expenses
INSERT INTO financials_last12mo (property_id, gross_income, net_operating_income, total_expenses, created_at, updated_at)
VALUES (:property_id::uuid, :gross_income, :net_operating_income, :total_expenses, now(), now())
ON CONFLICT (property_id) DO UPDATE
  SET gross_income = EXCLUDED.gross_income,
      net_operating_income = EXCLUDED.net_operating_income,
      total_expenses = EXCLUDED.total_expenses,
      updated_at = now()
RETURNING id;

-- 8) Insert a lease
-- Params: property_id, tenant_name, leased_sqft, lease_start, lease_end, rent_psf, source, raw_payload
INSERT INTO leases (property_id, tenant_name, leased_sqft, lease_start, lease_end, rent_psf, source, raw_payload, created_at)
VALUES (:property_id::uuid, :tenant_name, :leased_sqft, :lease_start::date, :lease_end::date, :rent_psf::numeric, :source, :raw_payload::jsonb, now())
RETURNING id;

-- 9) Create an agent task (idempotent via request_id)
-- Params: task_id, agent_name, property_id, run_mode, user_id, request_id
INSERT INTO agent_tasks (task_id, agent_name, property_id, run_mode, user_id, status, request_id, created_at, updated_at)
VALUES (:task_id, :agent_name, :property_id::uuid, :run_mode, :user_id::uuid, 'queued', :request_id, now(), now())
ON CONFLICT (request_id) DO NOTHING
RETURNING id, task_id, status;

-- 10) Update agent task status and append log entry
-- Params: task_id, status, log_msg
UPDATE agent_tasks
SET status = :status,
    log = COALESCE(log, '[]'::jsonb) || jsonb_build_array(jsonb_build_object('t', now(), 'msg', :log_msg)),
    updated_at = now()
WHERE task_id = :task_id
RETURNING id, status, log;

-- 11) Insert structured report
-- Params: property_id, report_id, summary, sections, confidence_overall, generated_at
INSERT INTO reports (id, property_id, report_id, summary, sections, confidence_overall, generated_at, created_at)
VALUES (gen_random_uuid(), :property_id::uuid, :report_id, :summary, :sections::jsonb, :confidence_overall::numeric, COALESCE(:generated_at, now()), now())
RETURNING id, report_id;

-- 12) Record approval
-- Params: report_id, user_id, decision, notes
INSERT INTO approvals (report_id, user_id, decision, notes, created_at)
VALUES (:report_id::uuid, :user_id::uuid, :decision, :notes, now())
RETURNING id;

-- 13) Fetch a report with provenance and related docs
-- Params: report_id
SELECT r.*, p.*
FROM reports r
LEFT JOIN provenance_entries p ON p.property_id = r.property_id
WHERE r.report_id = :report_id
ORDER BY p.fetched_at DESC;

-- 14) Find properties that need human review (any low-confidence provenance)
-- Params: threshold, limit
SELECT DISTINCT prop.*
FROM properties prop
JOIN provenance_entries pe ON pe.property_id = prop.id
WHERE pe.confidence < COALESCE(:threshold::numeric, 0.6)
ORDER BY prop.updated_at DESC
LIMIT COALESCE(:limit::int, 100);

-- 15) Proximity search (nearest properties to a lat/lon)
-- Params: lat, lon, limit
-- Requires earthdistance extension (ll_to_earth). For PostGIS replace with ST_Distance.
SELECT p.*, round(earth_distance(ll_to_earth(p.lat, p.lon), ll_to_earth(:lat::double precision, :lon::double precision))) AS distance_m
FROM properties p
WHERE p.lat IS NOT NULL AND p.lon IS NOT NULL
ORDER BY distance_m
LIMIT COALESCE(:limit::int, 10);

-- 16) Text similarity search on title (pg_trgm)
-- Params: q, limit
SELECT *, similarity(title, :q) AS sim
FROM properties
WHERE title ILIKE ('%' || :q || '%') OR similarity(title, :q) > 0.25
ORDER BY sim DESC
LIMIT COALESCE(:limit::int, 10);

-- 17) Insert an audit log event
-- Params: user_id, event_type, payload
INSERT INTO audit_logs (user_id, event_type, payload)
VALUES (:user_id::uuid, :event_type, :payload::jsonb);

-- 18) Transactional ingest example (client should run as a single transaction)
-- Params used inline: provider, provider_id, prop_id, raw_payload, field_path, fetched_confidence, fetched_raw_value
BEGIN;

-- 1) find existing property by source id
-- (client should call the SELECT above and branch if not found)

-- 2) attach source id (example)
INSERT INTO property_source_ids (property_id, provider, provider_id, raw_payload)
VALUES (:prop_id::uuid, :provider, :provider_id, :raw_payload::jsonb)
ON CONFLICT (property_id, provider, provider_id) DO UPDATE
  SET raw_payload = COALESCE(property_source_ids.raw_payload, EXCLUDED.raw_payload);

-- 3) insert provenance
INSERT INTO provenance_entries (property_id, field_path, provider, raw_reference, fetched_at, confidence, raw_value)
VALUES (:prop_id::uuid, :field_path, :prov_provider, :raw_reference, COALESCE(:fetched_at, now()), :fetched_confidence::numeric, :fetched_raw_value::jsonb);

COMMIT;
