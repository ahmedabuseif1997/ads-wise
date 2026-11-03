# Meta App Review — submission draft

**Status: draft. Do not submit until the owner confirms.** Nothing here has been sent to Meta.

| | |
|---|---|
| App | Ads-Wise- Agent · App ID `1418356733153531` · category Business |
| Business Manager | `1401711459689233` |
| Product | Marketing API + Facebook Login for Business (configuration ID in `META_LOGIN_CONFIG_ID`) |
| Graph API | v26.0 |
| Website / platform | https://ads-wise.com (Web) |
| OAuth redirect URI | `https://ads-wise.com/api/integrations/meta/callback` |
| Privacy Policy | https://ads-wise.com/privacy |
| Terms of Service | https://ads-wise.com/terms |
| Data deletion instructions | https://ads-wise.com/data-deletion |

## Before submitting (owner checklist)

1. PR #8 merged and deployed, so the reviewer sees the flow described below.
2. Business verification complete for Business Manager `1401711459689233` (Security Center). Because Ads-Wise manages ads for other businesses, Meta may also ask for **Access Verification** (tech provider); complete it if the dashboard shows it.
3. App Settings → Basic: Privacy, Terms and Data-deletion URLs above, app domain `ads-wise.com`, app icon, contact email.
4. Data Use Checkup completed if the dashboard shows it.
5. A **reviewer test account** for Ads-Wise (email + password entered only in Meta's "test instructions" field, never in this file or a commit) whose workspace:
   - has a low workspace budget cap (e.g. AED 50) so a demonstration launch cannot overspend;
   - is connected to a Meta test or sandbox ad account where possible.
6. Seed configured in Vercel (`ARK_API_KEY`, `ARK_BASE_URL`, `ARK_MODEL`), otherwise the launch demo is blocked by design.
7. Record one screencast (see below) and reuse the relevant parts per permission.

## Permissions requested (least privilege)

Requested: `ads_read`, `ads_management`, `pages_show_list`, `pages_read_engagement`.

Not requested:
- `business_management`: Ads-Wise never manages Business Manager assets. The owner removed it from the Login for Business configuration, and Seed validation no longer requires it.
- `pages_manage_ads`.
- Any Instagram permission: Instagram accounts are read through the ad account.

### ads_read

**How Ads-Wise uses it.** Ads-Wise is a supervised advertising console for spa and wellness businesses. After a business owner connects their own Meta ad account through Facebook Login for Business, Ads-Wise reads that ad account's campaigns and insights (spend, impressions, clicks, conversions) and shows them in the business's private Ads-Wise workspace, so the owner can review performance next to their other channels. Data is shown only to members of that business's workspace and is never shared with other customers.

**Graph API used:** `GET /me/adaccounts`, `GET /act_{id}`, `GET /act_{id}/campaigns`, `GET /act_{id}/insights`, `GET /act_{id}/adspixels`, `GET /act_{id}/instagram_accounts`.

**Screencast:** steps 1–5 and 10.

### ads_management

**How Ads-Wise uses it.** The business owner can launch campaigns they approved and pause, enable or change the daily budget of campaigns in their own ad account. Every change is first requested in Ads-Wise, automatically validated (budget limits, asset ownership, token, permissions, ad policy review), and then must be explicitly approved by the business owner before Ads-Wise calls the Marketing API. Ads-Wise also lists the ad account's Pixels and Instagram accounts so the owner can choose which ones their ads use. An emergency stop pauses every campaign Ads-Wise launched.

**Graph API used:** `POST /act_{id}/campaigns`, `POST /act_{id}/adsets`, `POST /act_{id}/adcreatives`, `POST /act_{id}/ads`, `POST /{campaign_id}` (status), `POST /{adset_id}` (daily budget), plus the reads above.

**Screencast:** steps 7–9.

### pages_show_list

**How Ads-Wise uses it.** When connecting, the owner chooses which Facebook Page their ads run from. Ads-Wise lists the Pages the owner manages (and checks they have the Advertise task) so the owner can pick the correct one.

**Graph API used:** `GET /me/accounts?fields=id,name,tasks`.

**Screencast:** step 4.

### pages_read_engagement

**How Ads-Wise uses it.** In **AI Campaign Studio**, when Meta is the advertising channel, Ads-Wise shows the name and picture of the Facebook Page selected for the workspace and its 10 most recent posts (image, text and date) under **Your Facebook Page posts**. The advertiser can pick an eligible post with **Use as ad creative**. When they launch a campaign, that post is promoted as the ad (`object_story_id`), after automated validation and the business owner's approval. The data is read only when the advertiser clicks **Load 10 recent posts**, is shown only to that business's owner and managers, and is never stored. Follower and engagement data are not read.

**Graph API used:** `GET /{page-id}?fields=id,name,picture,access_token` (a Page token used for that request only), `GET /{page-id}/posts?fields=id,message,created_time,full_picture,permalink_url,is_eligible_for_promotion&limit=10`, and `GET /{post-id}` to confirm the chosen post before launch.

**Screencast:** step 6 (Page posts in AI Campaign Studio), then steps 7–8.

## Screencast script (one recording, about 4 minutes)

1. Open https://ads-wise.com/app and sign in with the reviewer test account.
2. Go to **Ad Accounts** → **Connect Meta Ads**. Show the Facebook Login for Business consent screen listing the requested permissions, select the business assets, and continue.
3. Back in Ads-Wise, show the confirmation and the **Meta Ads — Assets required** state.
4. Click **Choose Meta assets**: show the ad account, Facebook Page, Instagram account and Pixel lists, select them, and click **Verify & save for this workspace**.
5. Click **Check with Meta** and show the connection health (token, permissions, assets).
6. Go to **AI Campaign Studio** with **Meta Ads** as the channel. Under **Your Facebook Page posts**, click **Load 10 recent posts**, show the Page name, picture and posts, and click **Use as ad creative** on one post.
7. Go to **Campaigns** → **Request Meta launch** on an approved campaign. Show the selected Page post as the creative and the budget, then **Run Seed validation**.
8. Go to **Approvals**. Show every validation check passing, click **Approve & go live**, then open Meta Ads Manager and show the new campaign, ad set and ad.
9. In **Analytics**, click **Request pause** on that campaign, approve it in **Approvals**, and show it paused in Ads Manager.
10. Click **Sync Meta** and show spend, impressions, clicks and conversions.
11. Click **Disconnect** in Ad Accounts to show the connection and stored token being removed.

## Data handling answers (summary)

- **Purpose:** show the business its own ad performance, and make owner-approved changes to its own campaigns.
- **Storage:** the access token is encrypted at rest on the server and never sent to the browser. Metrics snapshots are stored per workspace and refreshed on sync.
- **Sharing:** Meta Platform Data is never sold or shared with other customers or third parties for their own purposes.
- **Processors:**
  - hosting: Vercel
  - database: managed PostgreSQL
  - transactional email: Resend, for owner approval notices; the email holds no Meta data
  - Seed AI review: BytePlus ModelArk. It receives the advertiser's own draft ad text and budget from Ads-Wise, not data retrieved from Meta.
- **Deletion:** **Disconnect** deletes the token, the asset selections and the bindings. The deletion process is described at https://ads-wise.com/data-deletion.
- **Security:**
  - `appsecret_proof` is sent on every call made with a user token
  - CSRF and session protection
  - each workspace's data is isolated
  - Meta rate-limit back-off

## After approval

Switch the app to Live mode if it isn't already, then tell the developer. Once you confirm, they'll check a real workspace end to end: connect → assets → health → sync → one owner-approved low-budget launch → pause.
