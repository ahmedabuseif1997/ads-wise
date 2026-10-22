# Deploying on Vercel (production)

## Current setup (verified 22 Oct 2026)

| Item | Value |
|---|---|
| Vercel project | `spa-ads-agent` |
| Framework preset | FastAPI (entry point `app/main.py`, object `app`) |
| Domains | `ads-wise.com`, `www.ads-wise.com`, `spa-ads-agent.vercel.app` |
| Database | PostgreSQL via `DATABASE_URL` |
| Deploy method so far | Vercel CLI from a local folder (no Git connection) |

## What gets uploaded

`.vercelignore` keeps these out of every deployment: `.env*` (except `.env.example`), `data/` and SQLite files, `.venv/`, caches, `.git/`, `docs/`, `tests/`, `scripts/` and the Docker files. Before it existed, CLI deploys also uploaded the local SQLite database.

## Recommended workflow: Git-connected deploys

1. Push the code to the private GitHub repo `ahmedabuseif1997/ads-wise` (see below).
2. Vercel → `spa-ads-agent` → **Settings → Git → Connect Git Repository** → choose `ads-wise`.
3. Set **Production Branch** to `main`.
4. From then on:
   - push or merge to `main` → production deploy to ads-wise.com;
   - push to any other branch or open a PR → a **Preview** deployment with its own URL, for testing before release.

Preview deployments use the **Preview** environment variables. Right now every variable is set for **Production** only, so a preview build will not have the database, OAuth or AI keys. Either add the variables to Preview (ideally with a separate test database) or treat previews as UI-only checks.

## First push to GitHub

Create an empty **private** repo `ads-wise` at https://github.com/new (no README, .gitignore or license), then from the project folder:

```bash
git init -b main
git add -A
git status --short | grep -E "\.env|data/|\.vercel|\.venv" && echo "STOP: secret files staged" || echo "OK: no secrets staged"
git commit -m "Initial commit: Adwise AI Marketing OS"
git remote add origin https://github.com/ahmedabuseif1997/ads-wise.git
git push -u origin main
```

## Manual deploy (still possible)

```bash
vercel          # preview
vercel --prod   # production
```

## Environment variables

Managed in Vercel → Project → **Settings → Environment Variables**. The full list is in [../environment.md](../environment.md). A change to a variable takes effect on the **next** deployment.

## Rollback

Vercel → **Deployments** → choose a previous good deployment → **Promote to Production** (or **Instant Rollback**).

## OAuth redirect URIs

If the production domain changes, update the redirect URIs in Google Cloud, Meta and TikTok, plus `PUBLIC_ORIGIN` and `ALLOWED_ORIGINS`.
