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

## Meta

Needs a Meta developer app with Marketing API permissions. Set `META_APP_ID`, `META_APP_SECRET`, `META_LOGIN_CONFIG_ID`, `META_GRAPH_VERSION`, and register the callback URL `<PUBLIC_ORIGIN>/api/integrations/meta/callback`. Publishing to Meta is connection-gated and not complete.

## TikTok

Needs a TikTok for Business developer app. Set `TIKTOK_APP_ID`, `TIKTOK_APP_SECRET`, `TIKTOK_AUTHORIZATION_URL` (from the app portal) and `TIKTOK_API_VERSION`, and register `<PUBLIC_ORIGIN>/api/integrations/tiktok/callback`. Not configured in production yet.

## Website tracking tag (Pixels & Tracking)

Each workspace gets one tag at `https://ads-wise.com/tracking/<workspace-id>.js`. It loads only the Meta and TikTok pixel IDs saved for that workspace, sends `PageView`, and exposes `adwiseTrack.lead()`, `adwiseTrack.booking()` and the `data-adwise-track="lead|booking"` markup hooks.

Install it only after the site's consent manager allows advertising cookies, then verify events in Meta Test Events and TikTok Events Manager.

## Email (Resend)

Registration and password-reset emails are sent through Resend using `RESEND_API_KEY` and `TRANSACTIONAL_FROM_EMAIL`. New registration requests are emailed to `REGISTRATION_INBOX`.
