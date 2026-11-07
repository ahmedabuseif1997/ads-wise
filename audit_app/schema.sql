-- Backend-only Supabase schema. No browser/API role receives access.
CREATE SCHEMA IF NOT EXISTS audit_private;
REVOKE ALL ON SCHEMA audit_private FROM PUBLIC, anon, authenticated;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='audit_runtime') THEN
    CREATE ROLE audit_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
  END IF;
END $$;
SET LOCAL search_path = audit_private, pg_catalog;
CREATE TABLE IF NOT EXISTS audit_tenants(id TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_users(id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL,
           password_hash TEXT NOT NULL, tenant_id TEXT NOT NULL REFERENCES audit_tenants(id));
CREATE TABLE IF NOT EXISTS audit_sessions(token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL
           REFERENCES audit_users(id), csrf TEXT NOT NULL, expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_attempts(id TEXT PRIMARY KEY, bucket TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS audit_attempt_bucket ON audit_attempts(bucket,created_at);
CREATE TABLE IF NOT EXISTS audit_connections(tenant_id TEXT PRIMARY KEY REFERENCES audit_tenants(id),
           refresh_token TEXT NOT NULL, customer_id TEXT UNIQUE, manager_id TEXT, account_name TEXT,
           currency TEXT, time_zone TEXT);
CREATE TABLE IF NOT EXISTS audit_oauth(state_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL,
           tenant_id TEXT NOT NULL, verifier TEXT NOT NULL, expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_reports(id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL
           REFERENCES audit_tenants(id), customer_id TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS audit_reports_tenant_date ON audit_reports(tenant_id,created_at);
CREATE INDEX IF NOT EXISTS audit_users_tenant ON audit_users(tenant_id);
CREATE INDEX IF NOT EXISTS audit_sessions_user ON audit_sessions(user_id);
CREATE INDEX IF NOT EXISTS audit_oauth_tenant ON audit_oauth(tenant_id);
CREATE INDEX IF NOT EXISTS audit_oauth_user ON audit_oauth(user_id);
GRANT USAGE ON SCHEMA audit_private TO audit_runtime;
ALTER TABLE audit_tenants ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON audit_tenants FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON audit_tenants TO audit_runtime;
CREATE POLICY audit_backend_access ON audit_tenants TO audit_runtime USING (true) WITH CHECK (true);
ALTER TABLE audit_users ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON audit_users FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON audit_users TO audit_runtime;
CREATE POLICY audit_backend_access ON audit_users TO audit_runtime USING (true) WITH CHECK (true);
ALTER TABLE audit_sessions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON audit_sessions FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON audit_sessions TO audit_runtime;
CREATE POLICY audit_backend_access ON audit_sessions TO audit_runtime USING (true) WITH CHECK (true);
ALTER TABLE audit_attempts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON audit_attempts FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON audit_attempts TO audit_runtime;
CREATE POLICY audit_backend_access ON audit_attempts TO audit_runtime USING (true) WITH CHECK (true);
ALTER TABLE audit_connections ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON audit_connections FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON audit_connections TO audit_runtime;
CREATE POLICY audit_backend_access ON audit_connections TO audit_runtime USING (true) WITH CHECK (true);
ALTER TABLE audit_oauth ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON audit_oauth FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON audit_oauth TO audit_runtime;
CREATE POLICY audit_backend_access ON audit_oauth TO audit_runtime USING (true) WITH CHECK (true);
ALTER TABLE audit_reports ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON audit_reports FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON audit_reports TO audit_runtime;
CREATE POLICY audit_backend_access ON audit_reports TO audit_runtime USING (true) WITH CHECK (true);
-- Policies authorize only the trusted backend role. Tenant membership is enforced by
-- the API; anon/authenticated cannot use this schema or these policies.
