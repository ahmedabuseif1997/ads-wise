"""Independent, read-only Adswise audit service. No main-app imports or credentials."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parent
ORIGIN = os.getenv('AUDIT_PUBLIC_ORIGIN', 'http://localhost:8001').rstrip('/')
DATABASE_URL = os.getenv('AUDIT_DATABASE_URL', '').strip()
DB_PATH = Path(os.getenv('AUDIT_DB_PATH', str(ROOT / 'data' / 'audit.db')))
SECURE = os.getenv('AUDIT_COOKIE_SECURE', 'true').lower() == 'true'
SIGNUP_CODE = os.getenv('AUDIT_SIGNUP_CODE', '')
CLIENT_ID = os.getenv('AUDIT_GOOGLE_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('AUDIT_GOOGLE_CLIENT_SECRET', '')
DEVELOPER_TOKEN = os.getenv('AUDIT_GOOGLE_DEVELOPER_TOKEN', '')
ENCRYPTION_KEY = os.getenv('AUDIT_TOKEN_ENCRYPTION_KEY', '')
API_VERSION = os.getenv('AUDIT_GOOGLE_API_VERSION', 'v26')
COOKIE = '__Host-adswise_audit' if SECURE else 'adswise_audit_local'
CALLBACK = ORIGIN + '/api/google/callback'

if os.getenv('VERCEL'):
    if not DATABASE_URL or not SECURE or not ORIGIN.startswith('https://'):
        raise RuntimeError('Audit production requires its own database, HTTPS origin and Secure cookies')
    if DATABASE_URL == os.getenv('DATABASE_URL'):
        raise RuntimeError('Audit must not use the main Adswise database')


@contextmanager
def database():
    if DATABASE_URL:
        import psycopg
        from psycopg.rows import dict_row
        db = psycopg.connect(DATABASE_URL, row_factory=dict_row, prepare_threshold=None, connect_timeout=10)
        # SET LOCAL is scoped to this transaction, including through Supavisor transaction pooling.
        db.execute('SET LOCAL search_path TO audit_private, pg_catalog')
    else:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(DB_PATH, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
    class Connection:
        def lock(self, key):
            if DATABASE_URL:
                number = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], 'big', signed=True)
                db.execute('SELECT pg_advisory_xact_lock(%s)', (number,))
            else:
                db.execute('BEGIN IMMEDIATE')

        def execute(self, sql, params=()):
            return db.execute(sql.replace('?', '%s') if DATABASE_URL else sql, params)
    try:
        yield Connection()
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def one(db, sql, params=()):
    row = db.execute(sql, params).fetchone()
    return dict(row) if row else None


def init_db():
    if DATABASE_URL:
        # Hosted schema is provisioned through schema.sql, never by the runtime role.
        with database() as db:
            for table in ('audit_tenants', 'audit_users', 'audit_sessions', 'audit_attempts',
                          'audit_connections', 'audit_oauth', 'audit_reports'):
                db.execute(f'SELECT 1 FROM {table} LIMIT 0')
        return
    # Separate database AND table namespace prevent accidental reuse of main users/sessions.
    statements = [
        'CREATE TABLE IF NOT EXISTS audit_tenants(id TEXT PRIMARY KEY, name TEXT NOT NULL)',
        '''CREATE TABLE IF NOT EXISTS audit_users(id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL,
           password_hash TEXT NOT NULL, tenant_id TEXT NOT NULL REFERENCES audit_tenants(id))''',
        '''CREATE TABLE IF NOT EXISTS audit_sessions(token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL
           REFERENCES audit_users(id), csrf TEXT NOT NULL, expires_at TEXT NOT NULL)''',
        '''CREATE TABLE IF NOT EXISTS audit_attempts(id TEXT PRIMARY KEY, bucket TEXT NOT NULL, created_at TEXT NOT NULL)''',
        'CREATE INDEX IF NOT EXISTS audit_attempt_bucket ON audit_attempts(bucket,created_at)',
        '''CREATE TABLE IF NOT EXISTS audit_connections(tenant_id TEXT PRIMARY KEY REFERENCES audit_tenants(id),
           refresh_token TEXT NOT NULL, customer_id TEXT UNIQUE, manager_id TEXT, account_name TEXT,
           currency TEXT, time_zone TEXT)''',
        '''CREATE TABLE IF NOT EXISTS audit_oauth(state_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL,
           tenant_id TEXT NOT NULL, verifier TEXT NOT NULL, expires_at TEXT NOT NULL)''',
        '''CREATE TABLE IF NOT EXISTS audit_reports(id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL
           REFERENCES audit_tenants(id), customer_id TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL)''',
    ]
    with database() as db:
        db.lock('schema-init')
        for statement in statements:
            db.execute(statement)


def now():
    return datetime.now(timezone.utc).isoformat()


def expiry(seconds):
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    hashed = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return salt + ':' + hashed


def cipher():
    if not ENCRYPTION_KEY:
        raise HTTPException(503, 'Google token encryption is not configured')
    try:
        return Fernet(ENCRYPTION_KEY.encode())
    except ValueError:
        raise HTTPException(503, 'Google token encryption configuration is invalid')


def origin_check(request):
    # All browser mutations must originate on the audit app, including login/signup.
    if request.headers.get('origin', '').rstrip('/') != ORIGIN:
        raise HTTPException(403, 'Origin not allowed')


def user(request: Request):
    token = request.cookies.get(COOKIE, '')
    with database() as db:
        row = one(db, '''SELECT u.id,u.email,u.tenant_id,t.name,s.csrf FROM audit_sessions s
            JOIN audit_users u ON u.id=s.user_id JOIN audit_tenants t ON t.id=u.tenant_id
            WHERE s.token_hash=? AND s.expires_at>?''', (digest(token), now()))
    if not token or not row:
        raise HTTPException(401, 'Sign in to your audit account')
    return row


def writer(request: Request, current=Depends(user)):
    origin_check(request)
    if not hmac.compare_digest(request.headers.get('x-csrf-token', ''), current['csrf']):
        raise HTTPException(403, 'CSRF validation failed')
    return current


def throttle(db, bucket, limit=8, seconds=900):
    # Caller serializes the transaction across serverless instances before counting.
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()
    db.execute('DELETE FROM audit_attempts WHERE bucket=? AND created_at<?', (bucket, cutoff))
    count = one(db, 'SELECT COUNT(*) AS n FROM audit_attempts WHERE bucket=?', (bucket,))['n']
    if count >= limit:
        return False
    db.execute('INSERT INTO audit_attempts VALUES(?,?,?)', (secrets.token_hex(16), bucket, now()))
    return True


def limit_request(request, purpose, identifier='', limit=8, seconds=900):
    # Use the platform's resolved client address, not an arbitrary client-supplied forwarding header.
    ip = request.client.host if request.client else 'unknown'
    with database() as db:
        db.lock('rate-limits')
        allowed = throttle(db, digest(purpose + ':' + ip), limit, seconds)
        if identifier:
            allowed = throttle(db, digest(purpose + ':account:' + identifier), limit, seconds) and allowed
    if not allowed:
        raise HTTPException(429, 'Too many requests. Please try again later.')


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator('email')
    @classmethod
    def email_valid(cls, value):
        value = value.strip().lower()
        if '@' not in value or any(c.isspace() for c in value):
            raise ValueError('Enter a valid email address')
        return value


class Signup(Credentials):
    business: str = Field(min_length=1, max_length=100)
    invitation_code: str = Field(min_length=1, max_length=200)

    @field_validator('business')
    @classmethod
    def business_valid(cls, value):
        if not value.strip():
            raise ValueError('Enter a business name')
        return value.strip()


class Selection(BaseModel):
    customer_id: str = Field(pattern=r'^\d{10}$')
    manager_id: str = Field(default='', pattern=r'^(\d{10})?$')


class AuditOptions(BaseModel):
    offers_home_visits: bool = False
    goal: str = Field(default='bookings', pattern=r'^(bookings|enquiries)$')


@asynccontextmanager
async def lifespan(application):
    init_db()
    yield


app = FastAPI(title='Adswise Audit', docs_url=None, redoc_url=None, lifespan=lifespan)


@app.middleware('http')
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    if SECURE:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    return response


app.mount('/assets', StaticFiles(directory=ROOT / 'static'), name='assets')


@app.get('/')
def index():
    return FileResponse(ROOT / 'static' / 'index.html')


@app.get('/api/health')
def health():
    with database() as db:
        db.execute('SELECT 1 FROM audit_tenants LIMIT 0')
    return {'status': 'ok', 'service': 'adswise-audit', 'mode': 'read-only', 'database': 'ready'}


def sign_in(response, user_id):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
    with database() as db:
        db.execute('DELETE FROM audit_sessions WHERE expires_at<?', (now(),))
        db.execute('INSERT INTO audit_sessions VALUES(?,?,?,?)', (digest(token), user_id, csrf, expiry(86400)))
    response.set_cookie(COOKIE, token, max_age=86400, httponly=True, secure=SECURE, samesite='lax', path='/')
    return {'ok': True}


@app.post('/api/signup')
def signup(body: Signup, request: Request, response: Response):
    origin_check(request)
    limit_request(request, 'signup', body.email, limit=5)
    if not SIGNUP_CODE or not hmac.compare_digest(body.invitation_code, SIGNUP_CODE):
        raise HTTPException(403, 'A valid audit pilot invitation code is required')
    uid, tid = secrets.token_hex(16), secrets.token_hex(16)
    hashed = password_hash(body.password)
    with database() as db:
        db.lock('signup')
        if one(db, 'SELECT id FROM audit_users WHERE email=?', (body.email,)):
            raise HTTPException(409, 'Unable to create account. Try signing in instead.')
        db.execute('INSERT INTO audit_tenants VALUES(?,?)', (tid, body.business.strip()))
        db.execute('INSERT INTO audit_users VALUES(?,?,?,?)', (uid, body.email, hashed, tid))
    return sign_in(response, uid)


@app.post('/api/login')
def login(body: Credentials, request: Request, response: Response):
    origin_check(request)
    limit_request(request, 'login', body.email)
    with database() as db:
        found = one(db, 'SELECT * FROM audit_users WHERE email=?', (body.email,))
    salt = found['password_hash'].split(':')[0] if found else '00' * 16
    candidate = password_hash(body.password, salt)
    if not found or not hmac.compare_digest(candidate, found['password_hash']):
        raise HTTPException(401, 'Invalid email or password')
    return sign_in(response, found['id'])


@app.get('/api/me')
def me(current=Depends(user)):
    with database() as db:
        connection = one(db, '''SELECT customer_id,manager_id,account_name,currency FROM audit_connections
            WHERE tenant_id=?''', (current['tenant_id'],))
    return {**current, 'connection': connection, 'google_configured': bool(CLIENT_ID and CLIENT_SECRET and DEVELOPER_TOKEN and ENCRYPTION_KEY)}


@app.post('/api/logout')
def logout(request: Request, response: Response, current=Depends(writer)):
    with database() as db:
        db.execute('DELETE FROM audit_sessions WHERE token_hash=?', (digest(request.cookies[COOKIE]),))
    response.delete_cookie(COOKIE, path='/', secure=SECURE, httponly=True, samesite='lax')
    return {'ok': True}


def google_request(url, *, data=None, payload=None, headers=None):
    try:
        with httpx.Client(timeout=30) as client:
            result = client.post(url, data=data, json=payload, headers=headers)
        if result.status_code >= 400:
            if result.status_code in (400, 401):
                raise HTTPException(502, 'Google rejected the request. Check the connection, API configuration and account access.')
            raise HTTPException(502, 'Google could not complete the request. Check account permissions or try again later.')
        return result.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, 'Google is unavailable. Please try again later.')


def connection_for(tid):
    with database() as db:
        row = one(db, 'SELECT * FROM audit_connections WHERE tenant_id=?', (tid,))
    if not row:
        raise HTTPException(409, 'Connect your own Google Ads account first')
    return row


def access_token(connection):
    try:
        refresh = cipher().decrypt(connection['refresh_token'].encode()).decode()
    except InvalidToken:
        raise HTTPException(409, 'Reconnect Google Ads; the saved connection cannot be decrypted')
    result = google_request('https://oauth2.googleapis.com/token', data={
        'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'grant_type': 'refresh_token', 'refresh_token': refresh})
    return result['access_token']


def query_google(token, customer, query, manager=''):
    headers = {'Authorization': 'Bearer ' + token, 'developer-token': DEVELOPER_TOKEN}
    if manager:
        headers['login-customer-id'] = manager
    batches = google_request(f'https://googleads.googleapis.com/{API_VERSION}/customers/{customer}/googleAds:searchStream',
                             payload={'query': query}, headers=headers)
    return [row for batch in batches for row in batch.get('results', [])]


@app.post('/api/google/start')
def google_start(request: Request, current=Depends(writer)):
    if not (CLIENT_ID and CLIENT_SECRET and DEVELOPER_TOKEN):
        raise HTTPException(503, 'Google Ads is not configured for this audit deployment yet')
    cipher()
    limit_request(request, 'google-connect', current['id'], limit=5)
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    with database() as db:
        db.execute('DELETE FROM audit_oauth WHERE expires_at<? OR user_id=?', (now(), current['id']))
        db.execute('INSERT INTO audit_oauth VALUES(?,?,?,?,?)', (digest(state), current['id'], current['tenant_id'], verifier, expiry(600)))
    params = {'client_id': CLIENT_ID, 'redirect_uri': CALLBACK, 'response_type': 'code',
              'scope': 'https://www.googleapis.com/auth/adwords', 'access_type': 'offline',
              'prompt': 'consent select_account', 'state': state,
              'code_challenge': challenge, 'code_challenge_method': 'S256'}
    return {'url': 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode(params)}


@app.get('/api/google/callback')
def google_callback(state: str = '', code: str = '', error: str = '', current=Depends(user)):
    # DELETE RETURNING atomically consumes state; it is bound to the signed-in audit user and tenant.
    with database() as db:
        pending = one(db, '''DELETE FROM audit_oauth WHERE state_hash=? AND user_id=? AND tenant_id=?
            AND expires_at>? RETURNING *''', (digest(state), current['id'], current['tenant_id'], now()))
    if not pending:
        raise HTTPException(400, 'Invalid or expired Google connection request')
    if error or not code:
        return RedirectResponse('/?google=cancelled', status_code=303)
    result = google_request('https://oauth2.googleapis.com/token', data={
        'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'code': code, 'redirect_uri': CALLBACK,
        'code_verifier': pending['verifier'], 'grant_type': 'authorization_code'})
    if not result.get('refresh_token'):
        raise HTTPException(409, 'Google did not issue offline access. Reconnect and grant consent.')
    encrypted = cipher().encrypt(result['refresh_token'].encode()).decode()
    with database() as db:
        db.lock('google-connections')
        # Reauthorization clears the previous account selection and reports; never mix account histories.
        db.execute('DELETE FROM audit_reports WHERE tenant_id=?', (current['tenant_id'],))
        db.execute('''INSERT INTO audit_connections(tenant_id,refresh_token) VALUES(?,?)
            ON CONFLICT(tenant_id) DO UPDATE SET refresh_token=excluded.refresh_token,
            customer_id=NULL,manager_id=NULL,account_name=NULL,currency=NULL,time_zone=NULL''', (current['tenant_id'], encrypted))
    return RedirectResponse('/?google=connected', status_code=303)


@app.post('/api/google/select')
def select_account(body: Selection, current=Depends(writer)):
    connection = connection_for(current['tenant_id'])
    token = access_token(connection)
    rows = query_google(token, body.customer_id,
        'SELECT customer.id, customer.descriptive_name, customer.currency_code, customer.time_zone, customer.manager FROM customer LIMIT 1', body.manager_id)
    if not rows or rows[0]['customer'].get('manager'):
        raise HTTPException(422, 'Choose an advertising account, not a manager account')
    account = rows[0]['customer']
    if str(account['id']) != body.customer_id:
        raise HTTPException(403, 'Google returned a different account')
    with database() as db:
        db.lock('google-connections')
        live = one(db, 'SELECT refresh_token FROM audit_connections WHERE tenant_id=?', (current['tenant_id'],))
        if not live or live['refresh_token'] != connection['refresh_token']:
            raise HTTPException(409, 'Google connection changed. Verify your account again.')
        existing = one(db, 'SELECT tenant_id FROM audit_connections WHERE customer_id=?', (body.customer_id,))
        if existing and existing['tenant_id'] != current['tenant_id']:
            raise HTTPException(409, 'This Google Ads account is already assigned to another audit tenant')
        db.execute('DELETE FROM audit_reports WHERE tenant_id=?', (current['tenant_id'],))
        db.execute('''UPDATE audit_connections SET customer_id=?,manager_id=?,account_name=?,currency=?,time_zone=?
            WHERE tenant_id=?''', (body.customer_id, body.manager_id, account.get('descriptiveName', body.customer_id),
            account.get('currencyCode', ''), account.get('timeZone', 'UTC'), current['tenant_id']))
    return {'ok': True}


@app.post('/api/google/disconnect')
def disconnect(current=Depends(writer)):
    with database() as db:
        db.lock('google-connections')
        db.execute('DELETE FROM audit_oauth WHERE tenant_id=?', (current['tenant_id'],))
        db.execute('DELETE FROM audit_reports WHERE tenant_id=?', (current['tenant_id'],))
        db.execute('DELETE FROM audit_connections WHERE tenant_id=?', (current['tenant_id'],))
    return {'ok': True}


def build_findings(campaigns, ads, terms, actions, options, start, end):
    findings = []
    def add(key, title, evidence, explanation, steps, follow_up='Review after seven days, allowing for conversion reporting delays.'):
        findings.append({'id': key, 'title': title, 'evidence': evidence, 'explanation': explanation,
                         'steps': steps, 'follow_up': follow_up})
    totals = {}
    for row in campaigns:
        campaign, metrics = row.get('campaign', {}), row.get('metrics', {})
        item = totals.setdefault(str(campaign['id']), {'name': campaign.get('name', ''), 'cost_micros': 0, 'conversions': 0.0})
        item['cost_micros'] += int(metrics.get('costMicros', 0))
        item['conversions'] += float(metrics.get('conversions', 0))
        if campaign.get('advertisingChannelType') == 'SEARCH' and campaign.get('networkSettings', {}).get('targetContentNetwork'):
            key = 'display-' + str(campaign['id'])
            if not any(f['id'] == key for f in findings):
                add(key, 'Review Display Network on ' + item['name'], 'Campaign settings show Display Network enabled.',
                    'Review network performance before deciding whether this Search campaign should focus on search traffic.',
                    ['Open this Search campaign in Google Ads.', 'Open Settings → Networks.', 'Review performance by network.',
                     'If Search-only traffic is your objective, deselect Google Display Network and save.'])
    for cid, item in totals.items():
        if item['cost_micros'] > 0 and item['conversions'] == 0:
            add('zero-' + cid, 'Investigate spending without recorded conversions',
                f"{item['name']}: {item['cost_micros']/1_000_000:.2f} account-currency units spent; zero conversions ({start}–{end}).",
                'This may reflect conversion lag, tracking issues or traffic quality. It does not establish the cause.',
                ['Check the campaign’s conversion goals and reporting delay.', 'Test the conversion journey using Tag Assistant.',
                 'Review search terms and the destination page.', 'Choose a change only after reviewing the evidence.'])
    if not options.offers_home_visits:
        matches = [r for r in terms if any(t in r.get('searchTermView', {}).get('searchTerm', '').lower()
                   for t in ('home massage', 'massage at home', 'home service', 'home visit')) and int(r.get('metrics', {}).get('costMicros', 0)) > 0]
        if matches:
            add('home-intent', 'Review paid searches about home visits',
                'Paid search terms include: ' + '; '.join(r['searchTermView']['searchTerm'] for r in matches[:5]),
                'You said home visits are not offered. Check each term’s meaning before excluding it.',
                ['Open the Search terms report.', 'Review the listed terms and their conversion results.',
                 'Select clearly irrelevant terms → Add as negative keyword.', 'Review match type and campaign scope before saving.'])
    for row in actions:
        action = row.get('conversionAction', {})
        if action.get('primaryForGoal') and action.get('status') == 'ENABLED':
            name = action.get('name', '')
            if options.goal == 'bookings' and any(t in name.lower() for t in ('whatsapp', 'direction', 'click')):
                add('goal-' + str(action.get('id')), 'Confirm what your primary conversion measures',
                    f'“{name}” is enabled and marked primary for its goal.',
                    'Its name suggests an intermediate action. A name alone does not establish its implementation or campaign-specific bidding use.',
                    ['Open Goals → Conversions and inspect this action.', 'Confirm what event fires the tag.',
                     'Review which campaigns use this goal.', 'Keep enquiry actions and confirmed bookings separate in reports.'])
    for row in ads:
        ad = row.get('adGroupAd', {}).get('ad', {})
        rsa = ad.get('responsiveSearchAd', {})
        over = [a.get('text', '') for a in rsa.get('headlines', []) if len(a.get('text', '')) > 30]
        over += [a.get('text', '') for a in rsa.get('descriptions', []) if len(a.get('text', '')) > 90]
        if over:
            add('copy-' + str(ad.get('id')), 'Review ad text length', '; '.join(over),
                'RSA headlines allow up to 30 characters and descriptions up to 90. Google applies the final validation.',
                ['Open the ad for editing.', 'Shorten the flagged text while preserving verified business facts.',
                 'Review the preview and destination, then save.'])
    return findings, totals


@app.post('/api/reports')
def run_audit(body: AuditOptions, request: Request, current=Depends(writer)):
    connection = connection_for(current['tenant_id'])
    customer = connection.get('customer_id')
    if not customer:
        raise HTTPException(409, 'Select and verify your Google Ads customer ID first')
    limit_request(request, 'audit', current['id'], limit=4, seconds=300)
    token = access_token(connection)
    try:
        today = datetime.now(ZoneInfo(connection.get('time_zone') or 'UTC')).date()
    except (KeyError, ValueError):
        raise HTTPException(409, 'Reconnect the account to refresh its time zone')
    start, end = (today - timedelta(days=14)).isoformat(), (today - timedelta(days=1)).isoformat()
    dates = f"segments.date BETWEEN '{start}' AND '{end}'"
    def query(sql):
        return query_google(token, customer, sql, connection.get('manager_id') or '')
    # Full streamed results, no LIMIT on dated data; failure aborts the report instead of implying a clean audit.
    campaigns = query('SELECT campaign.id, campaign.name, campaign.advertising_channel_type, '
        'campaign.network_settings.target_content_network, metrics.cost_micros, metrics.clicks, metrics.impressions, '
        f'metrics.conversions FROM campaign WHERE {dates}')
    ads = query('SELECT campaign.id, campaign.name, ad_group_ad.ad.id, ad_group_ad.ad.final_urls, '
        'ad_group_ad.ad.responsive_search_ad.headlines, ad_group_ad.ad.responsive_search_ad.descriptions, '
        f'metrics.cost_micros, metrics.conversions FROM ad_group_ad WHERE {dates} AND ad_group_ad.status != \'REMOVED\'')
    terms = query('SELECT campaign.name, search_term_view.search_term, metrics.cost_micros, metrics.conversions '
        f'FROM search_term_view WHERE {dates} AND metrics.cost_micros > 0')
    actions = query('SELECT conversion_action.id, conversion_action.name, conversion_action.status, '
        'conversion_action.primary_for_goal, conversion_action.type FROM conversion_action')
    findings, totals = build_findings(campaigns, ads, terms, actions, body, start, end)
    report = {'id': secrets.token_hex(16), 'created_at': now(), 'start': start, 'end': end,
              'customer_id': customer, 'currency': connection['currency'], 'account_name': connection['account_name'],
              'findings': findings, 'campaigns': list(totals.values()), 'ads': ads, 'conversion_actions': actions,
              'completed': [], 'options': body.model_dump(),
              'limits': ['This is a limited rule-based audit, not a complete account assessment.',
                         'Google may omit low-volume search terms for privacy.',
                         'Tracking tag firing, landing-page availability, image quality, bidding causes and booking outcomes are not verified.']}
    with database() as db:
        db.lock('google-connections')
        # Avoid persisting data if the tenant switched or disconnected its account during the Google requests.
        live = one(db, 'SELECT customer_id,refresh_token FROM audit_connections WHERE tenant_id=?', (current['tenant_id'],))
        if not live or live['customer_id'] != customer or live['refresh_token'] != connection['refresh_token']:
            raise HTTPException(409, 'Your connection changed during the audit. Please run it again.')
        db.execute('INSERT INTO audit_reports VALUES(?,?,?,?,?)', (report['id'], current['tenant_id'], customer, report['created_at'], json.dumps(report)))
    return report


@app.get('/api/reports/latest')
def latest_report(current=Depends(user)):
    with database() as db:
        row = one(db, 'SELECT payload FROM audit_reports WHERE tenant_id=? ORDER BY created_at DESC LIMIT 1', (current['tenant_id'],))
    return json.loads(row['payload']) if row else None


class Completion(BaseModel):
    finding_id: str = Field(max_length=100)
    completed: bool


@app.post('/api/reports/{report_id}/completion')
def complete(report_id: str, body: Completion, current=Depends(writer)):
    with database() as db:
        db.lock('google-connections')
        row = one(db, 'SELECT payload FROM audit_reports WHERE id=? AND tenant_id=?', (report_id, current['tenant_id']))
        if not row:
            raise HTTPException(404, 'Report not found')
        report = json.loads(row['payload'])
        if body.finding_id not in [f['id'] for f in report['findings']]:
            raise HTTPException(404, 'Finding not found')
        done = set(report['completed'])
        (done.add if body.completed else done.discard)(body.finding_id)
        report['completed'] = sorted(done)
        db.execute('UPDATE audit_reports SET payload=? WHERE id=? AND tenant_id=?', (json.dumps(report), report_id, current['tenant_id']))
    return report
