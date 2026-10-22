# Local development

## Requirements

- Python 3.12 (see `.python-version`)
- Node.js (only for `node --check app/static/app.js`)

## First-time setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Edit `.env` for local use:

```
ADMIN_EMAIL=you@example.com
ADMIN_PASSWORD=<at least 14 characters>
INITIAL_SPA_NAME=My Spa
COOKIE_SECURE=false
PUBLIC_ORIGIN=http://localhost:8000
ALLOWED_ORIGINS=http://localhost:8000
DB_PATH=./data/adsagent.db
```

Leave `DATABASE_URL` empty locally so the app uses SQLite. **Do not point a local copy at the production database.**

## Run

```bash
set -a; source .env; set +a
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000. `--reload` restarts the server whenever a Python file changes. Static files (HTML/CSS/JS) are read on each request, so a browser refresh shows front-end edits.

OAuth integrations (Google, Meta, TikTok) only work locally if `http://localhost:8000/...callback` is registered as a redirect URI in each provider's console and the matching credentials are in `.env`.

## Test

```bash
ADMIN_EMAIL=test@example.com ADMIN_PASSWORD=a-valid-test-password-long-123 COOKIE_SECURE=false \
  python -m pytest tests/ -q
node --check app/static/app.js
```

The same checks run in GitHub Actions on every push and pull request (`.github/workflows/tests.yml`). The suite had 25 passing tests on 22 Oct 2026.

## Making changes

1. Create a branch: `git checkout -b feature/<short-name>`.
2. Change code, run the tests above.
3. Commit and push; open a pull request.
4. Merge to `main` → Vercel deploys production (once the repo is connected; see [deployment/vercel.md](deployment/vercel.md)).

### Adding a static file

Static files are served by explicit routes. After adding `app/static/new-file.css`, add a matching route in `app/main.py`, following the existing `/assets/...` routes:

```python
@app.get('/assets/new-file.css')
def new_file_css():
    return FileResponse(ROOT / 'static' / 'new-file.css', media_type='text/css')
```

### Database changes

Tables are created on startup with `CREATE TABLE IF NOT EXISTS`. Adding a column to an existing table needs an explicit `ALTER TABLE` that works on both SQLite and PostgreSQL, because production already has the tables.
