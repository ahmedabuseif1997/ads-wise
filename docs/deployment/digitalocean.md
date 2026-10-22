# Private first deployment — DigitalOcean Droplet

**Deployment state:** This package has been built and locally tested; it has **not** been installed on a DigitalOcean server and has no public URL yet. You must carry out these host-level steps with access to your DigitalOcean account and domain DNS. Avoid the existing CRM production droplet for now.

## 1. Create dedicated infrastructure

Create a new Ubuntu LTS Droplet. Use SSH key authentication and enable automatic OS updates. Ensure the DigitalOcean firewall (and any host-level firewall) allows inbound TCP **22** from your admin IP, inbound TCP **80/443** from the Internet, and optionally UDP **443** (HTTP/3). Do not expose app port 8000 or SQLite.

Create a DNS A record for a **new subdomain you control**, such as `ads.spamanagement.co`, pointing to the new Droplet IP. This is a suggested domain, **not** a DNS change performed by this package. Ensure the name resolves before expecting Caddy to obtain certificates.

## 2. Install Docker and Compose

Follow the current [official Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/) and [Compose plugin](https://docs.docker.com/compose/install/linux/) instructions. Confirm:

```bash
docker --version
docker compose version
```

## 3. Upload application to the NEW server

From your local machine, upload/extract `spa_ads_agent_standalone.zip`, then:

```bash
cd spa_ads_agent_standalone
cp .env.example .env
chmod 600 .env
nano .env
```

Set the following **before first boot**:

```
ADS_DOMAIN=ads.spamanagement.co
PUBLIC_ORIGIN=https://ads.spamanagement.co
COOKIE_SECURE=true
ADMIN_EMAIL=<your-private-admin-email>
ADMIN_PASSWORD=<new-random-unique-password-at-least-14-chars>
INITIAL_SPA_NAME=<your-spa-name>
DB_PATH=/app/data/adsagent.db
```

Keep `AI_API_KEY` blank until you intend to use and pay for a model provider. Do not publish `.env` in Git. Do not reuse credentials from the live Spa CRM repository.

## 4. Launch

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail 100 ads-agent
docker compose logs --tail 100 caddy
```

Then verify `https://ads.spamanagement.co/api/health` returns `{ "status": "ok", ... }` and check that HTTPS uses a valid certificate. Open the site, sign in, set a budget cap, create a campaign draft, and confirm the pending → internal approved workflow. **No real advertising account will be connected.**

After the owner is successfully seeded, remove `ADMIN_PASSWORD` (and optionally `ADMIN_EMAIL`) from `.env`; restart safely with `docker compose up -d` and verify you can still log in. Store credentials in a password manager.

## 5. Backup + recovery

The Docker volume `ads_data` contains all operational data. Set up scheduled off-server encrypted backups before storing production business information. SQLite supports online consistent backups through `sqlite3.Connection.backup`.

Example: create a backup file *inside* the running app volume (adjust timestamp and location):

```bash
docker compose exec -T ads-agent python -c \
"import sqlite3,datetime; p='/app/data/adsagent.db'; b='/app/data/backup-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')+'.db'; src=sqlite3.connect(p); dst=sqlite3.connect(b); src.backup(dst); print(b); dst.close(); src.close()"
```

Copy the named backup file off the host using `docker compose cp ads-agent:/app/data/backup-YYYYMMDD-HHMMSS.db ./backup.db`; encrypt and send to a private object-storage backup destination. Test restoring a backup on a separate host.

## 6. Restrict / monitor

- Recommended first launch: admin-only private use; consider firewall/IP allowlisting or VPN access while development continues.
- Monitor server logs, failed logins, disk usage and SQLite backups.
- Deploy updates from a reviewed version, not directly from an in-progress development branch.
- A production multi-customer public rollout needs security hardening, 2FA, operational observability, tested restores and platform connectors (see [`SECURITY.md`](../../SECURITY.md)).
- Never touch the existing CRM deployment Compose/project, existing DB, Caddyfile or credentials.

## Blockers to **actual** public deployment

A DigitalOcean authenticated deployment environment, new host/domain configuration, credentials and authorization to create resources. **None of these credentials or a public deployment were available to the assistant preparing this package.**
