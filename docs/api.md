# HTTP API reference

All routes are defined in `app/main.py`. `{tenant_id}` is a workspace ID. Every `/api/workspaces/{tenant_id}/…` route requires a signed-in member of that workspace. Every `POST` from a signed-in user also needs the `X-CSRF-Token` header; the token is returned by `GET /api/bootstrap`.

## Pages and static assets

| Method | Path | Serves |
|---|---|---|
| GET | `/` | Landing page |
| GET | `/app` | Signed-in application |
| GET | `/signup` | Registration page |
| GET | `/reset-password` | Password reset page |
| GET | `/super-admin` | Super-admin console (super-admin session required) |
| GET | `/privacy`, `/terms`, `/data-deletion` | Legal pages |
| GET | `/assets/<file>` | CSS, JS and images from `app/static/` (one explicit route per file) |
| GET | `/manifest.webmanifest`, `/service-worker.js` | PWA files |
| GET | `/tracking/{tenant_id}.js` | Per-workspace website tracking tag |

## Health

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness check (used by Docker health checks) |

## Accounts and sessions

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/register` | Submit a registration request |
| POST | `/api/login` | Sign in, sets the session cookie |
| POST | `/api/logout` | Sign out |
| POST | `/api/forgot-password` | Email a password reset link |
| POST | `/api/reset-password` | Set a new password with a reset token |
| GET | `/api/bootstrap` | Current user, CSRF token and workspaces |

## Super-admin

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/admin/overview` | Platform overview |
| POST | `/api/admin/registration-requests/{request_id}/{decision}` | Approve or reject a registration |

## Workspaces

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/workspaces` | Create a workspace |
| GET | `/api/workspaces/{tenant_id}` | Workspace detail (campaigns, settings, connections, snapshots) |
| POST | `/api/workspaces/{tenant_id}/invitations` | Invite a user |
| POST | `/api/invitations/{invite_token}/accept` | Accept an invitation |
| POST | `/api/workspaces/{tenant_id}/settings` | Update mode / approval cap |
| POST | `/api/workspaces/{tenant_id}/tracking` | Save pixel IDs and tracking events |
| POST | `/api/workspaces/{tenant_id}/emergency-stop` | Stop new approvals and planning |
| POST | `/api/workspaces/{tenant_id}/resume-automation` | Lift the emergency stop |

## Campaigns

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/workspaces/{tenant_id}/campaigns` | Create a draft |
| POST | `/api/workspaces/{tenant_id}/campaigns/{campaign_id}/submit` | Submit for approval |
| POST | `/api/workspaces/{tenant_id}/campaigns/{campaign_id}/approve` | Approve |
| POST | `/api/workspaces/{tenant_id}/campaigns/{campaign_id}/reject` | Reject |
| POST | `/api/workspaces/{tenant_id}/campaigns/{campaign_id}/archive` | Archive |
| POST | `/api/workspaces/{tenant_id}/campaigns/{campaign_id}/publish/google-search` | Publish an approved campaign to Google Ads (created paused) |
| POST | `/api/workspaces/{tenant_id}/campaigns/{campaign_id}/publish/meta` | Meta publishing (connection-gated) |

## AI planner

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/workspaces/{tenant_id}/agent/recommend-campaign` | Source-grounded campaign recommendation |
| POST | `/api/workspaces/{tenant_id}/agent/plan` | Campaign plan / draft generation |

## Google Ads

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/workspaces/{tenant_id}/integrations/google/start` | Begin OAuth |
| GET | `/api/integrations/google/callback` | OAuth callback |
| GET | `/api/workspaces/{tenant_id}/integrations/google/accounts` | List accessible Ads accounts |
| POST | `/api/workspaces/{tenant_id}/integrations/google/account` | Select the Ads account |
| POST | `/api/workspaces/{tenant_id}/integrations/google/sync` | Pull metrics |
| POST | `/api/workspaces/{tenant_id}/integrations/google/conversions/setup` | Create conversion actions |
| POST | `/api/workspaces/{tenant_id}/integrations/google/campaigns/{campaign_id}/status` | Pause / enable a live campaign |
| POST | `/api/workspaces/{tenant_id}/integrations/google/disconnect` | Disconnect |

## Google Growth (Business Profile, Search Console, GA4)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/workspaces/{tenant_id}/integrations/google-growth/start` | Begin OAuth |
| GET | `/api/integrations/google-growth/callback` | OAuth callback |
| POST | `/api/workspaces/{tenant_id}/integrations/google-growth/sync` | Pull Business Profile, Search Console and GA4 data (the SEO Console "Sync data" button) |
| POST | `/api/workspaces/{tenant_id}/integrations/google-growth/search-console-property` | Select the Search Console property |
| POST | `/api/workspaces/{tenant_id}/integrations/google-growth/analytics-property` | Select the GA4 property ("Use this property") |
| POST | `/api/workspaces/{tenant_id}/integrations/google-growth/sitemaps` | Submit a sitemap to Search Console |
| POST | `/api/workspaces/{tenant_id}/integrations/google-growth/disconnect` | Disconnect |

## Meta and TikTok

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/workspaces/{tenant_id}/integrations/meta/start` | Begin Meta OAuth |
| GET | `/api/integrations/meta/callback` | Meta OAuth callback |
| POST | `/api/workspaces/{tenant_id}/integrations/tiktok/start` | Begin TikTok authorization |
| GET | `/api/integrations/tiktok/callback` | TikTok callback |
| POST | `/api/workspaces/{tenant_id}/integrations/{provider}/disconnect` | Disconnect Meta or TikTok |
