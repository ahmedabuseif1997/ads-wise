# Adswise Audit

Independent Google Ads audit app for the proposed `audit.ads-wise.com` subdomain. It lives in the Adswise repository but uses a separate Vercel project, database, user accounts, encrypted tenant connections and host-only session cookie. Nothing in `app/main.py` is imported or changed.

This is an invitation-only pilot, not a complete implementation of the supplied spa playbook. It uses deterministic rules; no AI keys, model calls, browser agents or Google Ads mutations exist in this service.

## Included

- Separate signup/login/logout, salted scrypt password hashes, one workspace per new account, database-backed rate limiting and CSRF/origin checks.
- Google authorization using **the existing Adswise Google OAuth application and Google Ads developer token**. Use the existing approved scope; do not create a replacement Google application or developer-token application. Each tenant grants its own consent; connections/tokens are not copied from main Adswise.
- State bound to the user and tenant, PKCE, one-time callback state, encrypted refresh tokens, direct or manager-account customer-ID verification, exclusive account assignment inside the audit app.
- Last 14 complete days, using Google's account time zone and currency; campaign performance, actual RSA text/final URLs, search terms and conversion action definitions.
- Findings for Display Network enabled on Search, campaign spend with zero reported conversions, selected home-service search terms when not offered, potentially intermediate primary conversion actions, and RSA text limits.
- Evidence, manual Google Ads instructions, saved completion status and print/PDF output. Report and connection operations derive the tenant from the session.
- Disconnect deletes the tenant's connection, pending OAuth state and saved reports. It does not revoke the OAuth app's Google-wide grant, which could also affect main Adswise; users can revoke it themselves in Google account settings.

## Local testing

From the repository root after installing `requirements-dev.txt`:

```bash
export AUDIT_PUBLIC_ORIGIN=http://localhost:8001
export AUDIT_COOKIE_SECURE=false
# Enter a generated pilot invitation code into your local environment; never commit it.
export AUDIT_SIGNUP_CODE='<local pilot code>'
python -m uvicorn audit_app.main:app --reload --port 8001
```

Open exactly `http://localhost:8001` (origin checks are exact). Create an account with the invitation code. SQLite is only for local development. `.env` files are not loaded automatically.

Without configured Google credentials you can test signup/login and see the pending-setup message. Live audit buttons require an authorized and verified Google Ads account. Automated tests mock Google responses and never access real advertising accounts:

```bash
python -m pytest tests/test_audit_app.py -q
node --check audit_app/static/audit.js
```

## Staging setup status (7 November 2026)

- Vercel project created: `adswise-audit` (`prj_zdlTA0BngiS3popdFfHHAFtK5rgs`) in team `team_5CTlokwNst5caFkIIs7qKp07`.
- [Project dashboard](https://vercel.com/httpsgithubcomahmedabuseif1997nexora-crmg/adswise-audit). Repository connected; root directory configured as `audit_app`, FastAPI preset.
- `audit.ads-wise.com` is assigned to preview branch `feat/separate-audit-app`; Vercel confirms domain ownership. DNS routing and HTTPS service are not yet verified.
- Preview configuration present: `AUDIT_PUBLIC_ORIGIN=https://audit.ads-wise.com`, `AUDIT_COOKIE_SECURE=true`, `AUDIT_GOOGLE_API_VERSION=v26`.
- No audit deployment has been created, no database provisioned, no migration run, and no DNS or Google Cloud setting changed. Main Adswise production remains unchanged. PR #18 remains a draft.
- Missing Preview secrets: `AUDIT_DATABASE_URL`, `AUDIT_GOOGLE_CLIENT_ID`, `AUDIT_GOOGLE_CLIENT_SECRET`, `AUDIT_GOOGLE_DEVELOPER_TOKEN`, `AUDIT_TOKEN_ENCRYPTION_KEY`, `AUDIT_SIGNUP_CODE`. Enter them directly in the new project's environment settings; do not paste values into chat or GitHub.
- Existing Google client credentials in the main Vercel project are write-only Secret variables and cannot be exported by this connection. No `GOOGLE_ADS_DEVELOPER_TOKEN` was listed in the main project's environment metadata. Reuse the existing Google OAuth application and any existing approved developer token; a new OAuth application is not required.
- Create a new audit-only staging PostgreSQL database via the project's Storage tab and set `AUDIT_DATABASE_URL` (do not reuse the main database). Choose the provider plan explicitly; no paid storage was ordered.
- In the existing Google Cloud OAuth client's authorized redirect URIs, add `https://audit.ads-wise.com/api/google/callback` while preserving all existing URIs.
- Authoritative DNS is external (`dns1.registrar-servers.com`, `dns2.registrar-servers.com`). Vercel returned the required CNAME target `7b9202f64d9b984a.vercel-dns-017.com.` for host `audit`. Add only that subdomain record at the authoritative provider, preserving all other records. Recheck Vercel's current recommendation before applying if setup is resumed later.
- After secrets and database are ready, deploy the reviewed audit commit to Preview, verify PostgreSQL initialization and the real account consent/report flow, then verify DNS and HTTPS. Do not merge or deploy the main Adswise project as part of this step.

## Deployment procedure

1. Create a **separate Vercel project** from this repository, with **Root Directory `audit_app`** and the FastAPI framework preset. `main.py` exports `app`; native FastAPI routing needs no catch-all rewrite. Python 3.12 and dependencies are declared inside this root. See [Vercel FastAPI documentation](https://vercel.com/docs/frameworks/backend/fastapi).
2. Use a **new audit-only PostgreSQL database and credentials**, and a separate test database for previews. Do not set the main app's `DATABASE_URL`, admin bootstrapping variables or AI secrets in this project. `AUDIT_DATABASE_URL` must point to the audit database. Production refuses SQLite, insecure cookies, or an HTTP origin. If both database URL variables are present with identical values, startup fails.
3. Set `AUDIT_PUBLIC_ORIGIN=https://audit.ads-wise.com`, `AUDIT_COOKIE_SECURE=true`, `AUDIT_SIGNUP_CODE` to a new private pilot invitation code, and `AUDIT_TOKEN_ENCRYPTION_KEY` to a new Fernet key. For example, generate the latter locally with `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'` and enter it directly in Vercel's secret configuration. Do not paste secrets into issues or PRs.
4. Reuse the **existing Adswise** client ID, client secret and developer token as the values of `AUDIT_GOOGLE_CLIENT_ID`, `AUDIT_GOOGLE_CLIENT_SECRET`, and `AUDIT_GOOGLE_DEVELOPER_TOKEN`. Do not copy tenant refresh tokens. `AUDIT_GOOGLE_API_VERSION` defaults to the main app's `v26`; verify availability under the existing developer token during staging.
5. In that **same Google Cloud OAuth client**, add the exact redirect URI `https://audit.ads-wise.com/api/google/callback`. Preserve all existing main-app redirect URIs and authorized domains. Keep the current Google Ads scope (`https://www.googleapis.com/auth/adwords`). Google does not provide a separate read-only Google Ads scope: read-only behavior is enforced by this service's available API operations. Reusing the app does not bypass user consent, existing test-user restrictions, developer-token access limits or any review Google may require for configuration changes.
6. Set up the custom subdomain in the new Vercel project and apply the DNS record **returned by Vercel**. Do not guess its target or change the main site's records.
7. Register approved pilot tenants and test with their own Google Ads accounts. Verify real API queries, diagnostics, currencies, manager-account access, and no cross-tenant reports before inviting more users. Run the API suite against the staging PostgreSQL database as well; automated local tests cover SQLite only.

The owner subsequently authorized staging setup. The status above records completed and blocked actions. Main Adswise production remains untouched; do not silently promote a staging build or change the main site.

## Deliberate limits and pilot operations

- Existing Adswise credentials do not log into this app; account creation is independent. Users are free to reuse their email, but should choose a separate password.
- No password recovery/change UI, email verification, multi-user invitations, tenant administration, 2FA or account-deletion UI yet. Do not open signup publicly before those flows and operational recovery are implemented. Signup is disabled if the pilot invitation code is missing.
- One tenant per audit user. The pilot does not link existing Adswise workspaces or their membership. The same Google Ads account cannot be assigned to two audit tenants; the independent main app's binding registry is not shared.
- Reports store ad text, metrics and selected search-term evidence. They are retained until account reselection, Google reauthorization or disconnect. Agree a time-based retention policy and deletion/recovery procedures before broader onboarding.
- No hourly/device trends, bidding/change-history diagnosis, asset-level performance, image review, landing-page fetching, tracking tag execution, booking attribution, automatic keyword exclusions or campaign changes. Conversion names only suggest what to inspect; they do not prove an event's implementation.
- A failed Google query aborts the report. A rule not triggering is not evidence that an account is healthy. Search-term reports can omit data for privacy. Directions, WhatsApp clicks and bookings are distinct outcomes.
- Google requests run synchronously with a 30-second timeout per request; review Vercel duration and account/report size before using large accounts. No background sync or automatic retries.
- Rate limits use database transactions/advisory locks across instances. Configure a trusted edge rate limiter as well before broad public access. The app intentionally does not trust arbitrary `X-Forwarded-For` headers.
- Completion is self-reported, not verification of a remote fix.
