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

Open exactly `http://localhost:8001` (origin checks are exact). Create an account with the invitation code. SQLite is only for local development. Hosted PostgreSQL uses the private `audit_private` schema, provisioned with `schema.sql`; the runtime role does not execute schema migrations. Prepared statements are disabled for Supavisor transaction pooling, and search_path is set with SET LOCAL inside every transaction. `.env` files are not loaded automatically.

Without configured Google credentials you can test signup/login and see the pending-setup message. Live audit buttons require an authorized and verified Google Ads account. Automated tests mock Google responses and never access real advertising accounts:

```bash
python -m pytest tests/test_audit_app.py -q
node --check audit_app/static/audit.js
```

## Staging setup status (7 November 2026)

- Vercel project: `adswise-audit` (`prj_zdlTA0BngiS3popdFfHHAFtK5rgs`) in team `team_5CTlokwNst5caFkIIs7qKp07`. [Dashboard](https://vercel.com/httpsgithubcomahmedabuseif1997nexora-crmg/adswise-audit). Repository connected, root directory `audit_app`, FastAPI preset.
- `audit.ads-wise.com` is assigned to preview branch `feat/separate-audit-app`. Vercel confirms ownership, but authoritative DNS is not configured, so this is not yet a working public custom domain.
- Supabase project: `vksodudvjcbyovkdoucc` (Adswise Audit), owner-approved Nexora General Trading organization, `ap-south-1` region. Seven audit tables are in `audit_private`, with RLS enabled and no anon/authenticated schema access. A dedicated `audit_runtime` role has DML access and cannot bypass RLS. Supabase security advisors returned no findings.
- `schema.sql` was applied as hosted migration `audit_private_schema`; apply it once on a fresh project. A separate hosted `audit_runtime_login` migration generated the backend password inside Supabase and stored it in Vault. Neither this repository nor the migration text contains the generated password.
- Preview secrets saved: `AUDIT_DATABASE_URL`, `AUDIT_TOKEN_ENCRYPTION_KEY`, `AUDIT_SIGNUP_CODE`. Database uses the verified Supavisor transaction endpoint `aws-0-ap-south-1.pooler.supabase.com:6543` and role `audit_runtime.vksodudvjcbyovkdoucc`, with TLS. Secret values are not shown in chat or source.
- Preview config: `AUDIT_PUBLIC_ORIGIN=https://audit.ads-wise.com`, `AUDIT_COOKIE_SECURE=true`, `AUDIT_GOOGLE_API_VERSION=v26`. Automatic Preview builds are re-enabled; the temporary Ignored Build Step has been cleared. Custom production auto-assignment remains off.
- Working preview: `https://adswise-audit-9yp22n1se.vercel.app`, deployment `dpl_4op8ygmQpwoZmHn3ukdEKSDYSXjb`, code commit `c1130c167d3ffc5d02971f5071d84ad50fb16916`. Vercel-protected checks returned HTTP 200 for `/` and `/api/health`; health confirmed `database: ready`. The earlier endpoint on `aws-1` failed with tenant not found; the verified `aws-0` endpoint resolves that failure.
- Local automated tests: 100 passed; desktop/mobile browser checks for signup, login, logout, escaping and completion were previously passed. Hosted signup/login mutations are not yet verified: the connector supports authenticated GET checks only, and the cloud executor's direct network path to the deployment was rejected. Supabase SQL inspection confirmed schema privileges; role impersonation in the SQL management connection is not permitted, and no privileges were broadened to bypass that restriction.
- Google still pending: `AUDIT_GOOGLE_CLIENT_ID`, `AUDIT_GOOGLE_CLIENT_SECRET`, `AUDIT_GOOGLE_DEVELOPER_TOKEN`, plus adding `https://audit.ads-wise.com/api/google/callback` to the existing Google OAuth client. Existing Google client credentials in main Vercel are write-only Secrets; authorized reads returned no usable value. No developer-token variable was listed in the main project's environment. Do not retrieve secrets from old deployment artifacts or replace/rotate the existing Google app.
- DNS still pending at the external authoritative provider (`dns1.registrar-servers.com`, `dns2.registrar-servers.com`): CNAME host `audit`, target `7b9202f64d9b984a.vercel-dns-017.com.`. Vercel continues to report `misconfigured: true`. Preserve unrelated records and recheck the recommendation before applying later.
- No main Adswise production, external DNS or Google Cloud configuration was changed. PR #18 remains a draft. Google Cloud and Namecheap account access are needed to complete the remaining setup; a browser integration was suggested for that work.

## Deployment procedure

1. Create a **separate Vercel project** from this repository, with **Root Directory `audit_app`** and the FastAPI framework preset. `main.py` exports `app`; native FastAPI routing needs no catch-all rewrite. Python 3.12 and dependencies are declared inside this root. See [Vercel FastAPI documentation](https://vercel.com/docs/frameworks/backend/fastapi).
2. Use the **dedicated audit-only Supabase PostgreSQL database and credentials**, and a separate test database for previews. Do not set the main app's `DATABASE_URL`, admin bootstrapping variables or AI secrets in this project. `AUDIT_DATABASE_URL` must point to the audit database. Hosted environments refuse SQLite, insecure cookies, or an HTTP origin. Apply `schema.sql` once before deployment; runtime startup verifies tables without schema changes. If both database URL variables are present with identical values, startup fails.
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

## Administrator and approvals

Apply `migrations/001_admin_access.sql` to existing dedicated Audit databases. Provision the owner in `audit_users` with a scrypt password hash and add its ID to `audit_admins` through a trusted database administrator. The runtime can read admin membership but cannot grant it. No public signup can create an admin.

Public signup stores a pending request and cannot create a session until the owner approves it. The owner sees requests and Approve/Reject controls after signing in, and can generate a private invitation link for one email. An invitation is an explicit pre-approval, expires after seven days, and can be used once. Only its hash is stored; URL fragments keep the code out of HTTP request URLs. Share links manually; the service sends no email. Rejected requests stay rejected until the owner deliberately issues an invitation. Main Adswise accounts and data remain separate.
