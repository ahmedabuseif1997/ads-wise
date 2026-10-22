# Environment variables

The app reads configuration only from environment variables. It does **not** load `.env` automatically. Locally, run `set -a; source .env; set +a` before starting it; on Vercel, set them under **Project → Settings → Environment Variables**.

Never commit real values. `.env` and `.env.*` are ignored by Git and by Vercel uploads; only `.env.example` (placeholders) is tracked.

"On Vercel" shows whether the variable was present in the `spa-ads-agent` **Production** environment on 22 Oct 2026 (names only, values were not read).

## Core

| Variable | Required | Purpose | On Vercel |
|---|---|---|---|
| `DATABASE_URL` | Production | PostgreSQL connection string. If set, PostgreSQL is used instead of SQLite | Yes |
| `DB_PATH` | Local | SQLite file path when `DATABASE_URL` is empty (default `data/adsagent.db`) | No |
| `ADMIN_EMAIL` | First boot | Creates the first administrator | Yes |
| `ADMIN_PASSWORD` | First boot | Password for that administrator (14+ characters) | No |
| `INITIAL_SPA_NAME` | First boot | Name of the first workspace | Yes |
| `SUPER_ADMIN_EMAILS` | Optional | Comma-separated super-admin emails; defaults to `ADMIN_EMAIL` | No |
| `COOKIE_SECURE` | Yes | `true` in production (HTTPS), `false` for local HTTP | Yes |
| `PUBLIC_ORIGIN` | Yes | Public base URL, used for OAuth redirects and links | Yes |
| `ALLOWED_ORIGINS` | Yes | Comma-separated origins allowed to call the API | Yes |
| `ADS_DOMAIN` | Self-hosted | Domain Caddy serves (Docker deployment) | Yes |

## Email (Resend)

| Variable | Purpose | On Vercel |
|---|---|---|
| `RESEND_API_KEY` | Sends registration and password-reset emails | Yes |
| `TRANSACTIONAL_FROM_EMAIL` | From address, e.g. `Adwise <noreply@ads-wise.com>` | Yes |
| `REGISTRATION_INBOX` | Where new registration requests are emailed (default `info@ads-wise.com`) | No (default used) |

## AI models

| Variable | Purpose | On Vercel |
|---|---|---|
| `MINIMAX_API_KEY`, `MINIMAX_BASE_URL`, `MINIMAX_MODEL` | Preferred AI provider | Yes |
| `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL` | Fallback AI provider | Key and model: yes; base URL: no |
| `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL` | Generic OpenAI-compatible provider (e.g. BytePlus ModelArk) | No |

If no provider is configured, the UI labels results "Template only (AI not configured)".

## Google Ads

| Variable | Purpose | On Vercel |
|---|---|---|
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | OAuth client for Google Ads | Yes |
| `GOOGLE_TOKEN_ENCRYPTION_KEY` | Fernet key that encrypts all stored OAuth tokens. **Changing it makes existing connections unreadable** | Yes |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Google Ads API developer token, sent as the `developer-token` header | **No** |

> `GOOGLE_ADS_CUSTOMER_ID` and `GOOGLE_ADS_LOGIN_CUSTOMER_ID` exist on Vercel but are not read anywhere in the current code.
>
> **Needs confirmation:** Google Ads API calls normally require a developer token. Check whether live Google Ads features work in production without `GOOGLE_ADS_DEVELOPER_TOKEN`.

## Google Growth (Business Profile, Search Console, GA4)

| Variable | Purpose | On Vercel |
|---|---|---|
| `GOOGLE_GROWTH_CLIENT_ID`, `GOOGLE_GROWTH_CLIENT_SECRET` | OAuth client from the Google Cloud project approved for these APIs | Yes |

## Meta

| Variable | Purpose | On Vercel |
|---|---|---|
| `META_APP_ID`, `META_APP_SECRET` | Meta app credentials | Yes |
| `META_LOGIN_CONFIG_ID` | Facebook Login for Business configuration | Yes |
| `META_GRAPH_VERSION` | Graph API version, e.g. `v26.0` | Yes |

## TikTok

| Variable | Purpose | On Vercel |
|---|---|---|
| `TIKTOK_APP_ID`, `TIKTOK_APP_SECRET` | TikTok for Business app credentials | No |
| `TIKTOK_AUTHORIZATION_URL` | Authorization URL copied from the TikTok app portal | No |
| `TIKTOK_API_VERSION` | e.g. `v2.0` | No |

TikTok is not configured in production yet.
