"""Boundary tests for the independent audit deployment; no live Google calls."""
import json
from urllib.parse import parse_qs, urlparse

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from audit_app import main as audit

ORIGIN = 'http://localhost:8001'
PASSWORD = 'private-pilot-password-123'


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, 'REQUIRE_APPROVAL', False)
    monkeypatch.setattr(audit, 'DATABASE_URL', '')
    monkeypatch.setattr(audit, 'DB_PATH', tmp_path / 'audit.db')
    monkeypatch.setattr(audit, 'ORIGIN', ORIGIN)
    monkeypatch.setattr(audit, 'CALLBACK', ORIGIN + '/api/google/callback')
    monkeypatch.setattr(audit, 'SECURE', False)
    monkeypatch.setattr(audit, 'COOKIE', 'adswise_audit_local')
    monkeypatch.setattr(audit, 'SIGNUP_CODE', 'pilot-invitation')
    monkeypatch.setattr(audit, 'CLIENT_ID', 'existing-adswise-client')
    monkeypatch.setattr(audit, 'CLIENT_SECRET', 'test-secret')
    monkeypatch.setattr(audit, 'DEVELOPER_TOKEN', 'existing-adswise-developer-token')
    monkeypatch.setattr(audit, 'ENCRYPTION_KEY', Fernet.generate_key().decode())
    with TestClient(audit.app) as client:
        yield client


def signup(client, email='one@example.com'):
    r = client.post('/api/signup', json={'email': email, 'password': PASSWORD,
        'business': '<Test Spa>', 'invitation_code': 'pilot-invitation'}, headers={'Origin': ORIGIN})
    assert r.status_code == 200, r.text
    current = client.get('/api/me').json()
    return current, {'Origin': ORIGIN, 'X-CSRF-Token': current['csrf']}


def connection(current, customer='1234567890'):
    with audit.database() as db:
        db.execute('INSERT INTO audit_connections VALUES(?,?,?,?,?,?,?)',
            (current['tenant_id'], audit.cipher().encrypt(b'refresh-secret').decode(), customer, '', 'Test account', 'USD', 'UTC'))


def save_report(current, rid='report-1', customer='1234567890'):
    payload = {'id': rid, 'findings': [{'id': 'fix-1'}], 'completed': []}
    with audit.database() as db:
        db.execute('INSERT INTO audit_reports VALUES(?,?,?,?,?)',
            (rid, current['tenant_id'], customer, audit.now(), json.dumps(payload)))


def test_separate_identity_and_csrf(app):
    assert app.get('/').status_code == 200
    assert 'separate Audit account' in app.get('/').text
    assert app.get('/assets/audit.js').status_code == 200
    assert app.get('/api/me').status_code == 401
    app.cookies.set('spa_ads_session', 'main-app-session')
    assert app.get('/api/me').status_code == 401
    current, headers = signup(app)
    assert app.post('/api/logout', json={}).status_code == 403
    assert app.post('/api/logout', json={}, headers={**headers, 'Origin': 'https://ads-wise.com'}).status_code == 403
    with audit.database() as db:
        stored = audit.one(db, 'SELECT password_hash FROM audit_users WHERE id=?', (current['id'],))
        tables = [r['name'] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert PASSWORD not in stored['password_hash']
    assert 'users' not in tables and 'sessions' not in tables
    assert app.post('/api/logout', json={}, headers=headers).status_code == 200
    assert app.get('/api/me').status_code == 401
    assert app.post('/api/login', json={'email':'one@example.com', 'password':PASSWORD}, headers={'Origin': ORIGIN}).status_code == 200


def test_invitation_and_signup_origin(app):
    body = {'email':'one@example.com', 'password':PASSWORD, 'business':'Spa', 'invitation_code':'wrong'}
    assert app.post('/api/signup', json=body).status_code == 403
    assert app.post('/api/signup', json=body, headers={'Origin':ORIGIN}).status_code == 403
    assert app.get('/api/me').status_code == 401


def test_tenant_cannot_read_or_modify_another_report(app):
    first, _ = signup(app)
    connection(first)
    save_report(first)
    app.cookies.clear()
    second, headers = signup(app, 'two@example.com')
    assert second['tenant_id'] != first['tenant_id']
    assert app.get('/api/reports/latest').json() is None
    assert app.get('/api/me').json()['connection'] is None
    assert app.post('/api/reports/report-1/completion', json={'finding_id':'fix-1','completed':True}, headers=headers).status_code == 404
    assert app.post('/api/reports', json={}, headers=headers).status_code == 409


def test_completion_persists_and_disconnect_erases_only_own_data(app):
    current, headers = signup(app)
    connection(current)
    save_report(current)
    r = app.post('/api/reports/report-1/completion', json={'finding_id':'fix-1','completed':True}, headers=headers)
    assert r.json()['completed'] == ['fix-1']
    assert app.get('/api/reports/latest').json()['completed'] == ['fix-1']
    assert app.post('/api/google/disconnect', json={}, headers=headers).status_code == 200
    assert app.get('/api/reports/latest').json() is None
    assert app.get('/api/me').json()['connection'] is None


def test_google_reuses_client_and_state_is_user_bound_one_time(app, monkeypatch):
    first, headers = signup(app)
    r = app.post('/api/google/start', json={}, headers=headers)
    params = parse_qs(urlparse(r.json()['url']).query)
    assert params['client_id'] == ['existing-adswise-client']
    assert params['redirect_uri'] == [ORIGIN + '/api/google/callback']
    assert params['code_challenge_method'] == ['S256']
    state = params['state'][0]
    first_cookies = dict(app.cookies)
    app.cookies.clear()
    signup(app, 'two@example.com')
    assert app.get('/api/google/callback', params={'state':state,'code':'code'}).status_code == 400
    app.cookies.clear()
    app.cookies.update(first_cookies)
    seen = []
    def fake(url, **kwargs):
        seen.append(kwargs['data'])
        return {'refresh_token':'realistic-refresh'}
    monkeypatch.setattr(audit, 'google_request', fake)
    assert app.get('/api/google/callback', params={'state':state,'code':'code'}, follow_redirects=False).status_code == 303
    assert seen[0]['code_verifier']
    assert app.get('/api/google/callback', params={'state':state,'code':'code'}).status_code == 400
    with audit.database() as db:
        row = audit.one(db, 'SELECT * FROM audit_connections WHERE tenant_id=?', (first['tenant_id'],))
    assert row['customer_id'] is None
    assert 'realistic-refresh' not in row['refresh_token']
    assert 'refresh_token' not in app.get('/api/me').text


def test_cannot_select_other_tenants_account(app, monkeypatch):
    first, _ = signup(app)
    connection(first)
    app.cookies.clear()
    second, headers = signup(app, 'two@example.com')
    connection(second, '2222222222')
    monkeypatch.setattr(audit, 'access_token', lambda c: 'access')
    monkeypatch.setattr(audit, 'query_google', lambda *a: [{'customer': {'id':'1234567890','currencyCode':'USD','timeZone':'UTC'}}])
    assert app.post('/api/google/select', json={'customer_id':'1234567890'}, headers=headers).status_code == 409
    assert app.get('/api/me').json()['connection']['customer_id'] == '2222222222'


def test_live_audit_uses_reads_and_reports_evidence(app, monkeypatch):
    current, headers = signup(app)
    connection(current)
    calls = []
    def google(url, **kwargs):
        calls.append((url, kwargs))
        if url.endswith('/token'):
            return {'access_token':'access'}
        query = kwargs['payload']['query']
        assert ':searchStream' in url
        assert 'mutate' not in url
        assert kwargs['headers']['developer-token'] == 'existing-adswise-developer-token'
        if 'FROM campaign ' in query:
            rows = [{'campaign': {'id':'1','name':'Search','advertisingChannelType':'SEARCH','networkSettings':{'targetContentNetwork':True}},
                     'metrics':{'costMicros':'65000000','conversions':0}}]
        elif 'FROM ad_group_ad ' in query:
            rows = [{'adGroupAd':{'ad':{'id':'4','finalUrls':['https://example.com'], 'responsiveSearchAd':{'headlines':[{'text':'Massage in Abu Dhabi'}]}}}}]
        elif 'FROM search_term_view ' in query:
            rows = [{'searchTermView':{'searchTerm':'massage at home'},'metrics':{'costMicros':'12000000'}}]
        else:
            rows = [{'conversionAction':{'id':'8','name':'WhatsApp click','status':'ENABLED','primaryForGoal':True}}]
        return [{'results':rows}]
    monkeypatch.setattr(audit, 'google_request', google)
    r = app.post('/api/reports', json={'goal':'bookings', 'offers_home_visits':False}, headers=headers)
    assert r.status_code == 200, r.text
    report = r.json()
    assert report['currency'] == 'USD'
    assert report['campaigns'][0]['cost_micros'] == 65000000
    assert {f['id'] for f in report['findings']} == {'display-1','zero-1','home-intent','goal-8'}
    assert len(calls) == 5
    assert report['ads'][0]['adGroupAd']['ad']['id'] == '4'
    assert app.get('/api/reports/latest').json()['id'] == report['id']
    assert all('refresh-secret' not in json.dumps(f) for f in report['findings'])


def test_incomplete_google_read_does_not_save_a_clean_report(app, monkeypatch):
    current, headers = signup(app)
    connection(current)
    monkeypatch.setattr(audit, 'access_token', lambda c:'access')
    def unavailable(*args):
        raise audit.HTTPException(502, 'Google is unavailable')
    monkeypatch.setattr(audit, 'query_google', unavailable)
    assert app.post('/api/reports', json={}, headers=headers).status_code == 502
    assert app.get('/api/reports/latest').json() is None


def test_home_service_rule_respects_business_input():
    terms = [{'searchTermView': {'searchTerm':'home massage'}, 'metrics':{'costMicros':'1000000'}}]
    found, _ = audit.build_findings([], [], terms, [], audit.AuditOptions(offers_home_visits=True), 'start', 'end')
    assert found == []


def test_rate_limits_survive_new_clients(app):
    body = {'email':'missing@example.com', 'password':PASSWORD}
    for _ in range(8):
        assert app.post('/api/login', json=body, headers={'Origin':ORIGIN}).status_code == 401
    with TestClient(audit.app) as other:
        assert other.post('/api/login', json=body, headers={'Origin':ORIGIN}).status_code == 429


def test_short_audit_window_does_not_clear_login_rate_limit(app):
    with audit.database() as db:
        old = (audit.datetime.now(audit.timezone.utc) - audit.timedelta(seconds=600)).isoformat()
        db.execute('INSERT INTO audit_attempts VALUES(?,?,?)', ('older-login','login-bucket',old))
        assert audit.throttle(db, 'audit-bucket', seconds=300)
    with audit.database() as db:
        assert audit.one(db, 'SELECT id FROM audit_attempts WHERE bucket=?', ('login-bucket',))


def test_production_cookie_attributes(app, monkeypatch):
    monkeypatch.setattr(audit, 'SECURE', True)
    monkeypatch.setattr(audit, 'COOKIE', '__Host-adswise_audit')
    with TestClient(audit.app, base_url='https://audit.test') as secure:
        response = secure.post('/api/signup', json={'email':'secure@example.com','password':PASSWORD,
            'business':'Secure Spa','invitation_code':'pilot-invitation'}, headers={'Origin':ORIGIN})
        assert response.status_code == 200
        cookie = response.headers['set-cookie']
        assert '__Host-adswise_audit=' in cookie
        assert 'Secure' in cookie and 'HttpOnly' in cookie and 'Path=/' in cookie
        assert 'Domain=' not in cookie
        assert secure.get('/api/me').status_code == 200


def test_admin_approval_and_email_bound_invites(app, monkeypatch):
    admin_user, headers = signup(app, 'owner@example.com')
    with audit.database() as db:
        db.execute('INSERT INTO audit_admins VALUES(?)', (admin_user['id'],))
    monkeypatch.setattr(audit, 'REQUIRE_APPROVAL', True)
    other = TestClient(audit.app)
    payload = {'email':'waiting@example.com','password':PASSWORD,'business':'Waiting Spa'}
    response = other.post('/api/signup', json=payload, headers={'Origin':ORIGIN})
    assert response.json()['pending_approval'] is True
    assert other.get('/api/me').status_code == 401
    assert other.post('/api/login', json=payload, headers={'Origin':ORIGIN}).status_code == 401
    assert app.post('/api/admin/requests', json={'email':payload['email'],'action':'approve'}, headers=headers).status_code == 200
    assert other.post('/api/login', json=payload, headers={'Origin':ORIGIN}).status_code == 200
    member = other.get('/api/me').json()
    assert member['is_admin'] is False
    assert member['tenant_id'] != admin_user['tenant_id']
    assert other.get('/api/admin/requests').status_code == 403
    member_headers = {'Origin':ORIGIN,'X-CSRF-Token':member['csrf']}
    assert other.post('/api/admin/requests', json={'email':'bad@example.com','action':'invite'}, headers=member_headers).status_code == 403
    assert app.post('/api/admin/requests', json={'email':'x@example.com','action':'invite'}, headers={'Origin':ORIGIN}).status_code == 403
    invite = app.post('/api/admin/requests', json={'email':'invited@example.com','action':'invite'}, headers=headers).json()
    token = parse_qs(urlparse(invite['url']).fragment)['invite'][0]
    guest = TestClient(audit.app)
    invitation = {'email':'wrong@example.com','password':PASSWORD,'business':'Invited','invitation_code':token}
    assert guest.post('/api/signup', json=invitation, headers={'Origin':ORIGIN}).status_code == 403
    invitation['email'] = 'invited@example.com'
    assert guest.post('/api/signup', json=invitation, headers={'Origin':ORIGIN}).status_code == 200
    assert guest.post('/api/signup', json=invitation, headers={'Origin':ORIGIN}).status_code == 409
    assert guest.get('/api/me').json()['is_admin'] is False


def test_rejected_request_cannot_resubmit(app, monkeypatch):
    owner, headers = signup(app)
    with audit.database() as db:
        db.execute('INSERT INTO audit_admins VALUES(?)', (owner['id'],))
    monkeypatch.setattr(audit, 'REQUIRE_APPROVAL', True)
    guest = TestClient(audit.app)
    body = {'email':'reject@example.com','password':PASSWORD,'business':'Test'}
    guest.post('/api/signup', json=body, headers={'Origin':ORIGIN})
    app.post('/api/admin/requests', json={'email':body['email'],'action':'reject'}, headers=headers)
    guest.post('/api/signup', json=body, headers={'Origin':ORIGIN})
    with audit.database() as db:
        row = audit.one(db, 'SELECT * FROM audit_access_requests WHERE email=?', (body['email'],))
    assert row['status'] == 'rejected' and row['password_hash'] is None


def test_pwa_public_assets_and_private_api_boundary(app):
    manifest = app.get('/assets/manifest.webmanifest')
    assert manifest.status_code == 200
    data = manifest.json()
    assert data['display'] == 'standalone' and data['scope'] == '/'
    for icon in data['icons']:
        response = app.get(icon['src'])
        assert response.status_code == 200 and response.headers['content-type'] == 'image/png'
    worker = app.get('/sw.js')
    assert worker.status_code == 200
    assert worker.headers['service-worker-allowed'] == '/'
    assert 'javascript' in worker.headers['content-type']
    assert app.get('/assets/offline.html').status_code == 200
    assert app.get('/api/me').status_code == 401
    assert app.get('/api/reports/latest').status_code == 401
    assert app.get('/api/admin/requests').status_code == 401
