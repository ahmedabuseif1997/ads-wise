# Adwise — AI Marketing OS

Adwise is a multi-workspace paid-advertising and growth console for spa and wellness businesses. It plans, drafts, approves and (for Google Search) publishes ad campaigns, and connects each workspace to Google Ads, Google Business Profile, Search Console, Google Analytics 4, Meta and TikTok.

- **Production:** https://ads-wise.com (Vercel project `spa-ads-agent`)
- **Stack:** Python 3.12 · FastAPI · PostgreSQL in production (SQLite locally) · vanilla JS single-page app
- **Status:** private MVP — read [`SECURITY.md`](SECURITY.md) before onboarding unrelated customers.

## Repository layout

```
.
├── app/
│   ├── main.py            FastAPI backend: auth, sessions, tenants, integrations, AI planner, audit
│   └── static/            Front-end (HTML, CSS, JS, icons) served by FastAPI routes
├── tests/                 Pytest suite (API, security and behaviour tests)
├── scripts/               One-off operational scripts
├── docs/                  Project documentation (start at docs/README.md)
├── .github/workflows/     CI: pytest + JS syntax check on every push / PR
├── Dockerfile             Container image (self-hosted option)
├── compose.yaml           App + Caddy HTTPS proxy (self-hosted option)
├── Caddyfile              Caddy reverse-proxy config (self-hosted option)
├── requirements.txt       Runtime dependencies
├── requirements-dev.txt   Runtime + test dependencies
├── .env.example           Every supported environment variable, with safe placeholders
├── .gitignore             Keeps secrets, local DBs and virtualenvs out of Git
└── .vercelignore          Keeps secrets, local DBs and dev files out of Vercel uploads
```

## Quick start (local)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # then edit: see docs/development.md
set -a; source .env; set +a   # the app does not auto-load .env
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000. Full instructions: [`docs/development.md`](docs/development.md).

## Tests

```bash
ADMIN_EMAIL=test@example.com ADMIN_PASSWORD=a-valid-test-password-long-123 COOKIE_SECURE=false \
  python -m pytest tests/ -q
node --check app/static/app.js
```

## Super Admin and developer MCP

`/admin` shows deployment, database, API, AI and per-tenant integration health. Super Admins can pause a tenant or AI globally/per tenant. The optional `/mcp/developer` Streamable HTTP endpoint exposes only the approved developer-task queue and repository workflow; set a long random `MCP_AGENT_TOKEN` and configure that endpoint in Codex or Claude. It never exposes application secrets or a production shell.

## Documentation

| Topic | File |
|---|---|
| Documentation index | [`docs/README.md`](docs/README.md) |
| Architecture & data model | [`docs/architecture.md`](docs/architecture.md) |
| HTTP API reference | [`docs/api.md`](docs/api.md) |
| Environment variables | [`docs/environment.md`](docs/environment.md) |
| Local development | [`docs/development.md`](docs/development.md) |
| Deploy on Vercel (production) | [`docs/deployment/vercel.md`](docs/deployment/vercel.md) |
| Deploy on DigitalOcean (self-hosted) | [`docs/deployment/digitalocean.md`](docs/deployment/digitalocean.md) |
| Integrations (Google, Meta, TikTok, pixels) | [`docs/integrations.md`](docs/integrations.md) |
| Security model | [`SECURITY.md`](SECURITY.md) |

## Not built yet

Meta and TikTok publishing, image generation, CRM integration, end-to-end attribution and 2FA. Google publishing supports Search campaigns only, and new Google campaigns are always created **paused**.
