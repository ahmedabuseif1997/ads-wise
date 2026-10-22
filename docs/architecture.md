# Architecture

## Overview

Adwise is a single FastAPI application (`app/main.py`) that serves both the JSON API and the static front-end. There is no separate front-end build step: HTML, CSS and JavaScript in `app/static/` are returned as-is by explicit routes.

```
Browser (app/static/*.html, app.js)
        │  HTTPS, session cookie + X-CSRF-Token header
        ▼
FastAPI  app/main.py
        ├── Auth, sessions, CSRF, tenant membership checks
        ├── Campaign drafts → submit → approve/reject → archive
        ├── AI planner (MiniMax preferred, OpenAI fallback, template mode if neither)
        ├── Integrations: Google Ads, Google Growth, Meta, TikTok (OAuth, encrypted tokens)
        ├── Per-workspace tracking tag  /tracking/<workspace-id>.js
        └── Audit log
        │
        ▼
Database: PostgreSQL when DATABASE_URL is set (production), otherwise SQLite at DB_PATH
```

## Backend (`app/main.py`)

- **Framework:** FastAPI, served by Uvicorn locally and by Vercel's Python runtime in production.
- **Database layer:** a small wrapper chooses PostgreSQL (`psycopg`, when `DATABASE_URL` is set) or SQLite (`DB_PATH`, default `data/adsagent.db`). Tables are created on startup with `CREATE TABLE IF NOT EXISTS`.
- **Outbound HTTP:** `httpx` for Google, Meta, TikTok, MiniMax/OpenAI and Resend (email).

### Data model (tables)

| Table | Purpose |
|---|---|
| `users` | Accounts (scrypt-hashed passwords) |
| `sessions` | Session token hashes, per-session CSRF token, expiry (7 days) |
| `password_reset_tokens` | One-time password reset tokens |
| `registration_requests` | Sign-up requests awaiting super-admin approval |
| `tenants` | Workspaces (one per business) |
| `memberships` | Which user belongs to which workspace, and role |
| `invitations` | Pending workspace invitations |
| `tenant_settings` | Autonomy mode, approval cap, emergency stop |
| `campaigns` | Campaign drafts and their approval status |
| `campaign_specs` | Versioned detailed campaign payloads |
| `provider_connections` | OAuth connections per workspace (tokens encrypted) |
| `provider_snapshots` | Cached metrics pulled from Google / Meta / Search Console / GA4 |
| `provider_publications` | Record of what was published to an ad platform (duplicate protection) |
| `oauth_states` | Short-lived OAuth `state` values |
| `tracking_configs` | Pixel IDs per workspace for the tracking tag |
| `audit_log` | Who did what, when |

All workspace data is filtered by `tenant_id` and every workspace route checks membership.

## Security essentials

- Passwords: `hashlib.scrypt` (n=2^14, r=8, p=1) with a random salt.
- Sessions: random token in an HttpOnly cookie; only its SHA-256 hash is stored.
- CSRF: every state-changing request must send `X-CSRF-Token` matching the session (calls without it get `403 CSRF validation failed`).
- Third-party tokens: encrypted at rest with Fernet using `GOOGLE_TOKEN_ENCRYPTION_KEY`.
- Super-admin: emails listed in `SUPER_ADMIN_EMAILS` (falls back to `ADMIN_EMAIL`).
- Live ad-platform changes are always separate, confirmed actions; new Google campaigns are created paused.

See [`../SECURITY.md`](../SECURITY.md) for the full model and known limitations.

## Front-end (`app/static/`)

| File(s) | Role |
|---|---|
| `landing.html`, `landing.css`, `landing.js`, `cinematic.*`, `landing-footer.css` | Public marketing page at `/` |
| `index.html`, `app.js`, `style.css`, `dashboard-*.css`, `analytics.css`, `responsive-fixes.css`, `brand-palette.css` | The signed-in app at `/app` |
| `admin.html`, `admin.js`, `admin.css` | Super-admin console at `/super-admin` |
| `signup.*`, `reset-password.*` | Registration and password reset |
| `privacy.*`, `terms.html`, `data-deletion.html` | Legal pages |
| `manifest.webmanifest`, `service-worker.js`, icons | PWA assets |

Static files are reachable only through the explicit routes listed in [api.md](api.md). A new static file needs a new route in `main.py` before it can be loaded.

## Hosting

- **Production:** Vercel project `spa-ads-agent` (framework preset: FastAPI), domains `ads-wise.com` and `www.ads-wise.com`, PostgreSQL via `DATABASE_URL`. See [deployment/vercel.md](deployment/vercel.md).
- **Self-hosted alternative:** Docker Compose + Caddy. See [deployment/digitalocean.md](deployment/digitalocean.md).
