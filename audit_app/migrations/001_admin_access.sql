-- Apply only to the dedicated Audit database.
CREATE TABLE audit_private.audit_admins(user_id TEXT PRIMARY KEY REFERENCES audit_private.audit_users(id));
CREATE TABLE audit_private.audit_access_requests(email TEXT PRIMARY KEY,business TEXT NOT NULL,password_hash TEXT,status TEXT NOT NULL CHECK(status IN ('pending','invited','approved','rejected')),invite_hash TEXT,expires_at TEXT,created_at TEXT NOT NULL);
ALTER TABLE audit_private.audit_admins ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_private.audit_access_requests ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON audit_private.audit_admins,audit_private.audit_access_requests FROM PUBLIC,anon,authenticated;
GRANT SELECT ON audit_private.audit_admins TO audit_runtime;
GRANT SELECT,INSERT,UPDATE,DELETE ON audit_private.audit_access_requests TO audit_runtime;
CREATE POLICY audit_backend_access ON audit_private.audit_admins TO audit_runtime USING(true);
CREATE POLICY audit_backend_access ON audit_private.audit_access_requests TO audit_runtime USING(true) WITH CHECK(true);
