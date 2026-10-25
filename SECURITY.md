# Security and honest capability boundary

## MVP implemented controls

- Passwords stored as salted `scrypt` hashes. No default password or secrets shipped.
- Session token is random, stored as a SHA-256 hash, 7-day lifetime, HttpOnly SameSite=Lax; HTTPS deployment uses Secure cookies.
- CSRF header is required for all authenticated mutations; configured Origin checking; restrictive CSP/anti-frame headers.
- Login attempts throttled on a rolling per-IP 15-minute window in app memory.
- Each workspace read/write checks membership; mutations additionally require the owner role. All campaign, settings and audit queries scoped to workspace.
- Provider resources are exclusively bound at database level: one Google/Meta/TikTok ad account, GA4 property, Search Console site, or Business Profile account cannot be attached to two workspaces. Reauthorization clears stale snapshots without releasing the existing binding until replacement or explicit disconnect.
- All monetary values stored as integer fils, accepted to two AED decimal places. Workspace budget cap verified atomically using an SQLite write transaction.
- AI model credentials only read from server environment. AI responses never trigger ad publishing.
- There is **no** Google/Meta OAuth or publishing code and no route that can spend real money.
- The emergency stop blocks planning and approvals **inside this application only**. It cannot pause ads running independently on Google or Meta.

## BEFORE a public, multi-customer launch

1. Add first-class 2FA, account recovery, password changes, invitation and role administration, session management and secure administrator onboarding.
2. Harden rate limiting at the reverse proxy or dedicated distributed limiter; add security events and brute-force monitoring.
3. Add provider-specific OAuth with PKCE/state, approved scopes, encrypted refresh tokens, and a provider capability/version matrix. Do not confuse organic Page access with paid Ads permissions.
4. Implement a fail-closed publishing gateway with versioned human approvals, idempotency, reconciliation of uncertain writes, spend authorization, and provider-side budgets.
5. Plan for PostgreSQL and DB-level RLS before significant multi-tenant scale. SQLite can support an isolated small admin trial with backup discipline but is not the preferred long-term public SaaS persistence layer.
6. Define data retention, consent/privacy notice and regulatory review before collecting click identifiers, customer or conversion data.
7. Add security logging, intrusion detection, SLO monitoring, backup verification, restore drill, dependency alerts, vulnerability scans, pen-test, and incident procedures.
8. Do not describe internally approved drafts as live provider campaigns. Google/Meta API credentials, ad accounts and permission reviews are required to publish.

## Explicitly out of scope in this build

Real ad account connections, campaign create/pause/resume through Meta/Google, real performance metrics, CRM booking/sales conversions, autonomous spend, video/image generation, user invitations. The advertising agent is an **AI planning and controlled drafting MVP** until those capabilities are implemented and tested.
