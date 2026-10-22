# Claude Code prompt — continue a **standalone** Ads Agent to real deployment and platform integration

You have a working, tested private spa Ads Agent MVP in this package. **Do not edit or integrate into the production `chordsnstrings/massage-parlour-saas` repository.** Create a NEW standalone private repository, e.g. `spa-ads-agent`. Its current app has real local data, sessions, AI text via configurable compatible API, draft/submit/owner approve workflow and budget policies. Real ad OAuth/publishing/conversions are explicitly absent.

Start by reading `README.md`, `SECURITY.md`, `DEPLOY_DIGITALOCEAN.md`, the FastAPI backend/tests and static frontend. Run `pytest` and `node --check`. Validate the Docker build, Caddyfile and deployment settings. Open issues/PRs for any defects.

Your next responsibilities in order:

1. Provision a **separate** DigitalOcean resource and a dedicated subdomain AFTER owner approval and with the owner's connected/authorized DigitalOcean session. Never modify the active Spa CRM hosting/droplet or its repo.
2. Improve production security before a public launch: 2FA, safe recovery, team auth, password rotation, verified off-site backups, monitoring, rate limiting, security review, and move toward Postgres/RLS for scale.
3. Add secure official Meta Marketing API and Google Ads API OAuth and a provider status/account selector. Note that as of Sep 9, 2026 Google Ads API access tiers are tied to Google Cloud projects; don't base onboarding on a new developer token.
4. Add read-only real campaign sync and real metrics with timestamps; never fabricate conversion attribution.
5. Add gated provider campaign publishing on separate owner approval **after** the owner explicitly authorizes a real campaign. Use typed, versioned payloads, account/capability verification, safe idempotency, strict spending policy and reconcile uncertain remote writes.
6. Add CRM API integration **only after a separate approved integration contract**; do not reach directly into the live CRM DB. Track consent/UTM and real bookings/sales as distinct outcomes.
7. Add tests for provider failure/retries, budget concurrency, tenant isolation and launch approvals. Deployment and real ad spend remain independently approval-gated.

Deliver a working deployed URL and audit evidence only **after** a real deployment has succeeded. Any missing credentials or app approvals must be reported, never bypassed or simulated as live.
