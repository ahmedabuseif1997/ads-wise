# Integrations

Each workspace authorizes its own accounts. OAuth tokens are encrypted at rest with `GOOGLE_TOKEN_ENCRYPTION_KEY`, and connecting an account never authorizes live publishing by itself: every live campaign change is a separately confirmed action. Variable names are listed in [environment.md](environment.md).

## AI models

MiniMax is preferred when `MINIMAX_API_KEY`, `MINIMAX_BASE_URL` and `MINIMAX_MODEL` are set; OpenAI is the fallback. The recommendation endpoint builds a bounded source pack (the platform's official policy page and the advertiser's landing page) and validates the model output against the campaign recommendation schema. Results list consulted sources, confidence, assumptions and missing inputs, and never publish anything. No API key is sent to the browser or stored in campaign records.

## Google Ads

- OAuth with `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`; refresh tokens stored encrypted.
- Live metrics for Yesterday, This week, Last week and Last 30 days, using the Ads account's time zone.
- Conversion-action setup and supervised pause/enable of live campaigns.
- **Search campaign publishing** (approval-gated): daily budget, UAE/location and language targeting, phrase keywords, optional audience segments, responsive search ads, callouts and phone assets, created atomically and **paused**. Enabling is a separate confirmed action.
- Duplicate protection: versioned payload, deterministic remote name, local publication record and remote reconciliation before retries.

## Google Growth — Business Profile, Search Console, GA4 (the "SEO Console")

1. In the Google Cloud project approved for the Business Profile API, enable: Business Profile Account Management, Business Information, Search Console, Google Analytics Admin and Google Analytics Data APIs.
2. Set `GOOGLE_GROWTH_CLIENT_ID` and `GOOGLE_GROWTH_CLIENT_SECRET`.
3. Register the redirect URI `https://ads-wise.com/api/integrations/google-growth/callback`.

Behaviour:

- **Sync data** pulls the last 30 complete days of Search Console clicks, impressions, CTR, position, top queries and pages, plus GA4 active users, new users, sessions and events.
- A workspace can submit a sitemap only to a Search Console property returned by its own connection, and can select only a GA4 property returned by its own authorization.
- Connections made before Search Console management and Analytics read-only scopes were added must reconnect once.

## Meta Ads (Marketing API, Facebook Login for Business)

**Setup.** Meta app `1418356733153531` (Business Manager `1401711459689233`). Set `META_APP_ID`, `META_APP_SECRET`, `META_LOGIN_CONFIG_ID` and `META_GRAPH_VERSION` (`v26.0`, the latest Graph/Marketing API version). Register exactly `https://ads-wise.com/api/integrations/meta/callback` under *Facebook Login for Business → Settings → Valid OAuth Redirect URIs*. Permissions come from the Login for Business configuration, not from code (no `scope` parameter is sent).

**Least-privilege permissions.** Required: `ads_read`, `ads_management`, `pages_show_list`, `pages_read_engagement`. `business_management` is not requested (Adswise never manages Business Manager assets) and must not be in the Login for Business configuration. `pages_manage_ads` is not requested; add it only if Meta rejects Page-backed creatives for a Page. Instagram accounts are read through the ad account (`/act_…/instagram_accounts`), so no Instagram permission is needed.

**Tokens.** Meta issues no refresh tokens. The production Login for Business configuration (`1671511114491688`) issues **user access tokens**: the callback exchanges the code once and swaps the short-lived token for a long-lived one (≈60 days; health shows the days left and asks for a reconnect in the last 7 days). If Meta refuses that exchange for a user token, the connection is flagged as short-lived instead of failing silently. A system-user configuration keeps its non-expiring token. The callback verifies it with `debug_token` (app ID, validity, expiry, and granted permissions from both `scopes` and `granular_scopes`; Login for Business system-user tokens list `ads_read`/`ads_management` only in `granular_scopes`, and if Meta lists them in neither, a successful ad account read confirms them) and stores it encrypted with `GOOGLE_TOKEN_ENCRYPTION_KEY`. Every user-token call sends `appsecret_proof`. Tokens never reach the browser, logs or audit entries. Expired or revoked tokens (error 190) mark the connection `reauth_required`.

**Tenant isolation.** Each workspace authorizes its own Meta user. The owner chooses the ad account, Facebook Page, Instagram account and Pixel from what that user can access; every choice is verified live with Meta and bound to one workspace only (database-enforced). Reconnecting as a different Meta user clears the Page, Instagram and Pixel choices. Metrics snapshots are stored per workspace and ignored if they belong to a different ad account. A Pixel typed in *Pixels & Tracking* cannot be one used by another workspace or differ from the verified Pixel.

**Rate limits and cool-downs.** No automatic retries. The callback makes at most four Meta calls. Usage headers (`X-App-Usage`, `X-Business-Use-Case-Usage`, `X-Ad-Account-Usage`) are read on every response; at 85% or on a throttling error (4, 17, 32, 613, 80000+) Adswise pauses its own Meta calls for Meta's `estimated_time_to_regain_access` (default 7 minutes). The cool-down is stored in the database, so every server instance respects it. App-wide throttling pauses all workspaces; ad-account throttling pauses only that workspace. Login starts are limited to 5 per workspace per 15 minutes. The emergency pause still runs during a cool-down.

**Live changes: Seed validation then owner approval.** A manager, owner or AI agent can only *request* a launch, enable/pause or daily-budget change. Seed validation runs immediately:

1. Rule checks (deterministic): workspace active and emergency stop off; Meta connected; campaign belongs to the workspace and is awaiting launch; budget within the approved campaign budget and workspace cap; payload complete (HTTPS URLs, copy, Page, Pixel for booking/lead objectives); every asset bound to this workspace only; token valid for this app; required permissions granted; ad account active and billed in AED; Page/Instagram/Pixel still accessible; target campaign inside the workspace's ad account. Enabling and budget changes are limited to campaigns Adswise launched for the workspace; pausing works for any campaign in its ad account.
2. Seed AI review (`seed-2-0-pro-260328` on BytePlus ModelArk) of launches, enables and budget changes: fails on misleading copy, health claims, personal-attribute wording, adult wording or budget anomalies. It fails closed: if Seed is not configured, paused or unreachable, the request is blocked. Pausing never depends on the AI.

Only a 100% pass reaches the owner (in-app under *Approvals*, plus email when Resend is configured). On approval, the rule checks run again live; the Seed AI verdict is reused because the stored payload cannot change. The change then executes: launches create the campaign, ad set, creative and ad as **ACTIVE** using only the workspace's verified assets, and every step is written to the audit log. The emergency stop pauses every campaign Adswise launched for the workspace.

**Page posts as ad creatives (`pages_read_engagement`).** In AI Campaign Studio (Meta channel), owners and managers can load the 10 most recent posts of the workspace's selected Page (image, text, date, eligibility for promotion) and pick one as the ad creative. Only the selected Page is read; a Page token is fetched for that request and never stored; posts and follower data are not stored. A launch with a post (`object_story_id`) is accepted only for a post of the selected Page; Seed confirms it still exists and is eligible for promotion, and the Seed AI reviews the post's text as read from Meta.

**Sync.** Campaigns, effective status, spend, impressions, clicks and conversions (Pixel lead, schedule, contact, purchase and registration; the first matching action type per event is used, so totals are not double counted), cached per workspace for 5 minutes.

**Errors shown to users.** Expired or invalid token → reconnect. Missing permission → reconnect and approve all permissions (with Meta's reason). Unavailable asset → choose an asset the user can access. Throttling → cool-down with the retry time.

## Seed (BytePlus ModelArk)

Set `ARK_API_KEY` (server-side only), `ARK_BASE_URL=https://ark.ap-southeast.bytepluses.com/api/v3` and `ARK_MODEL=seed-2-0-pro-260328`. The BytePlus key cannot call the Volcano Engine defaults (`ark.cn-beijing.volces.com`, `doubao-seed-2-1-pro-260915`), so all three variables must match.

## TikTok

Needs a TikTok for Business developer app. Set `TIKTOK_APP_ID`, `TIKTOK_APP_SECRET`, `TIKTOK_AUTHORIZATION_URL` (from the app portal) and `TIKTOK_API_VERSION`, and register `<PUBLIC_ORIGIN>/api/integrations/tiktok/callback`. Not configured in production yet.

## Website tracking tag (Pixels & Tracking)

Each workspace gets one tag at `https://ads-wise.com/tracking/<workspace-id>.js`. It loads only the Meta and TikTok pixel IDs saved for that workspace, sends `PageView`, and exposes `adwiseTrack.lead()`, `adwiseTrack.booking()` and the `data-adwise-track="lead|booking"` markup hooks.

Install it only after the site's consent manager allows advertising cookies, then verify events in Meta Test Events and TikTok Events Manager.

## Email (Resend)

Registration and password-reset emails are sent through Resend using `RESEND_API_KEY` and `TRANSACTIONAL_FROM_EMAIL`. New registration requests are emailed to `REGISTRATION_INBOX`.
