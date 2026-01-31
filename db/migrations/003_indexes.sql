-- 003_indexes.sql
-- Indexes and performance optimizations

-- Properties
CREATE INDEX IF NOT EXISTS idx_properties_address_city_state ON properties(address_city, address_state);
CREATE INDEX IF NOT EXISTS idx_properties_geog ON properties USING GIST (ll_to_earth(lat, lon));
CREATE INDEX IF NOT EXISTS idx_properties_property_type ON properties(property_type);

-- Source ids
CREATE INDEX IF NOT EXISTS idx_property_source_ids_provider ON property_source_ids(provider, provider_id);

-- Provenance
CREATE INDEX IF NOT EXISTS idx_provenance_property_field ON provenance_entries(property_id, field_path);

-- Financials
CREATE INDEX IF NOT EXISTS idx_financials_property ON financials_last12mo(property_id);

-- Leases
CREATE INDEX IF NOT EXISTS idx_leases_property_tenant ON leases(property_id, tenant_name gin_trgm_ops);

-- Comps
CREATE INDEX IF NOT EXISTS idx_comps_property_date ON comps(property_id, sale_date);

-- Full text / similarity on property title
CREATE INDEX IF NOT EXISTS idx_properties_title_trgm ON properties USING gin (title gin_trgm_ops);

-- Agent tasks by status
CREATE INDEX IF NOT EXISTS idx_agent_tasks_status ON agent_tasks(status);

-- Reports by property
CREATE INDEX IF NOT EXISTS idx_reports_property ON reports(property_id);

-- Audit logs event_type
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type);
