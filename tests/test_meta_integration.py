"""Meta Marketing API integration: OAuth, assets, sync, health, Seed validation, owner approval, isolation.

Every Graph call is served by FakeMeta; no test ever reaches Meta or creates real ads.
"""
import json
import os
import re
import secrets
import time
from urllib.parse import parse_qs, urlparse

os.environ.setdefault('ADMIN_EMAIL', 'owner@example.com')
os.environ.setdefault('ADMIN_PASSWORD', 'really-long-integration-password-123')
os.environ.setdefault('COOKIE_SECURE', 'false')

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from app import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'DB_PATH', tmp_path / 'adsagent.db')
    for name in ('AI_API_KEY', 'MINIMAX_API_KEY', 'ARK_API_KEY', 'TIKTOK_APP_ID', 'TIKTOK_APP_SECRET',
                 'TIKTOK_AUTHORIZATION_URL', 'GOOGLE_GROWTH_CLIENT_ID', 'GOOGLE_GROWTH_CLIENT_SECRET',
                 'RESEND_API_KEY'):
        monkeypatch.setattr(main, name, '')
    main._LOGIN_ATTEMPTS.clear()
    main.init_db()
    with TestClient(main.app) as c:
        yield c


def session(client):
    r = client.post('/api/login', json={'email': os.environ['ADMIN_EMAIL'], 'password': os.environ['ADMIN_PASSWORD']})
    assert r.status_code == 200
    boot = client.get('/api/bootstrap').json()
    return boot['tenants'][0]['id'], {'X-CSRF-Token': boot['csrf']}


def meta_draft(**overrides):
    body = {'name': 'Wellness weekends', 'provider': 'meta', 'objective': 'bookings',
            'service': 'Spa Massage', 'brief': 'Promote our sessions', 'copy': 'Take time to unwind.',
            'landing_url': 'https://example.com/book', 'budget_aed': '200.00',
            'audience_location': 'Abu Dhabi, UAE', 'audience_age_min': 25, 'audience_age_max': 55,
            'audience_gender': 'all', 'audience_interests': 'massage, wellness',
            'placements': 'Instagram and Facebook feeds',
            'image_urls': 'https://cdn.example.com/massage.jpg', 'call_to_action': 'BOOK_NOW'}
    body.update(overrides)
    return body


def launch(daily='25', days=7):
    return {'version': 1, 'daily_budget_aed': daily, 'duration_days': days, 'countries': ['AE'],
            'interest_ids': [], 'primary_text': 'Book a relaxing massage today.', 'headline': 'Relax at Be Relax',
            'image_url': 'https://example.com/massage.jpg', 'final_url': 'https://example.com/book',
            'call_to_action': 'BOOK_NOW', 'conversion_event': 'SCHEDULE'}


class FakeMeta:
    """In-memory Graph API: two Meta users with their own (partly overlapping) assets."""

    def __init__(self):
        self.calls = []
        self.errors = {}
        self.next_id = 90000
        self.objects = {}
        self.codes = {'code-A': 'token-A', 'code-B': 'token-B'}
        self.users = {
            'token-A': {'user_id': 'meta-user-a', 'scopes': list(main.META_REQUIRED_SCOPES), 'valid': True,
                        'expires_in': 50 * 86400,
                        'ad_accounts': {'act_111': {'name': 'Spa A Ads', 'currency': 'AED',
                                                    'timezone_name': 'Asia/Dubai', 'account_status': 1}},
                        'pages': [{'id': '501', 'name': 'Spa A', 'tasks': ['ADVERTISE', 'ANALYZE']},
                                  {'id': '502', 'name': 'Analytics only', 'tasks': ['ANALYZE']}],
                        'instagram': {'act_111': [{'id': '601', 'username': 'spa_a'}]},
                        'pixels': {'act_111': [{'id': '70100001', 'name': 'Spa A Pixel'}]}},
            # An agency user who can also see Spa A's assets, which must stay exclusive to workspace A.
            'token-B': {'user_id': 'meta-user-b', 'scopes': list(main.META_REQUIRED_SCOPES), 'valid': True,
                        'expires_in': 50 * 86400,
                        'ad_accounts': {'act_222': {'name': 'Spa B Ads', 'currency': 'AED',
                                                    'timezone_name': 'Asia/Dubai', 'account_status': 1},
                                        'act_111': {'name': 'Spa A Ads', 'currency': 'AED',
                                                    'timezone_name': 'Asia/Dubai', 'account_status': 1}},
                        'pages': [{'id': '503', 'name': 'Spa B', 'tasks': ['ADVERTISE']},
                                  {'id': '501', 'name': 'Spa A', 'tasks': ['ADVERTISE']}],
                        'instagram': {'act_222': [], 'act_111': [{'id': '601', 'username': 'spa_a'}]},
                        'pixels': {'act_222': [{'id': '70200002', 'name': 'Spa B Pixel'}],
                                   'act_111': [{'id': '70100001', 'name': 'Spa A Pixel'}]}},
        }
        self.campaign_rows = {'act_111': [{'id': '8001', 'name': 'Existing A', 'status': 'ACTIVE',
                                           'effective_status': 'ACTIVE', 'objective': 'OUTCOME_TRAFFIC'}],
                              'act_222': []}
        self.insight_rows = {'act_111': [{'campaign_id': '8001', 'campaign_name': 'Existing A', 'spend': '120.50',
                                          'impressions': '10000', 'clicks': '250',
                                          'actions': [{'action_type': 'lead', 'value': '7'},
                                                      {'action_type': 'offsite_conversion.fb_pixel_lead', 'value': '7'},
                                                      {'action_type': 'schedule_total', 'value': '3'},
                                                      {'action_type': 'link_click', 'value': '250'}]}],
                             'act_222': []}
        self.daily_rows = {'act_111': [{'date_start': '2026-11-01', 'spend': '120.50', 'impressions': '10000',
                                        'clicks': '250', 'actions': [{'action_type': 'lead', 'value': '7'}]}],
                           'act_222': []}
        self.seed_reviews = []
        self.seed_verdict = {'decision': 'pass', 'summary': 'Clear, compliant spa offer.', 'issues': []}
        self.remote = {'8001': {'account': 'act_111', 'status': 'ACTIVE'},
                       '8002': {'account': 'act_222', 'status': 'ACTIVE'}}

    def posts(self):
        return [call for call in self.calls if call[0] == 'POST']

    def __call__(self, method, path, access_token='', params=None, timeout=25, allow_during_cooldown=False):
        params = dict(params or {})
        self.calls.append((method, path, access_token, params))
        if (method, path) in self.errors:
            raise self.errors[(method, path)]
        if path == 'oauth/access_token':
            if 'code' in params:
                assert params['redirect_uri'] == 'https://ads-wise.com/api/integrations/meta/callback'
                token = self.codes.get(params['code'])
                if not token:
                    raise main.MetaAPIError('invalid_request', 'Invalid verification code', 100)
                return {'access_token': f'short-{token}'}
            return {'access_token': params['fb_exchange_token'].removeprefix('short-')}
        if path == 'debug_token':
            assert params['access_token'] == f'{main.META_APP_ID}|{main.META_APP_SECRET}'
            user = self.users.get(params['input_token'])
            if not user:
                return {'data': {'is_valid': False, 'app_id': main.META_APP_ID}}
            return {'data': {'is_valid': user['valid'], 'app_id': user.get('app_id', main.META_APP_ID),
                             'user_id': user['user_id'], 'expires_at': user.get('expires_at', int(time.time()) + user.get('expires_in', 0)),
                             'data_access_expires_at': int(time.time()) + 80 * 86400, 'scopes': user['scopes'],
                             'granular_scopes': user.get('granular', [])}}
        user = self.users.get(access_token)
        if not user:
            raise main.MetaAPIError('token_invalid', 'Invalid OAuth access token', 190)
        granted = set(user['scopes']) | {item['scope'] for item in user.get('granular', [])}
        ad_access = user.get('ads_access', bool(granted & {'ads_read', 'ads_management'}))
        if (path == 'me/adaccounts' or re.match(r'act_\d+', path)) and not ad_access:
            raise main.MetaAPIError('missing_permission', '(#200) Requires ads_read or ads_management', 200)
        if path == 'me/adaccounts':
            return {'data': [{'id': key, 'account_id': key[4:], **value} for key, value in user['ad_accounts'].items()]}
        if path == 'me/accounts':
            return {'data': user['pages']}
        edge = re.fullmatch(r'(act_\d+)/(instagram_accounts|adspixels|campaigns|insights|adsets|adcreatives|ads)', path)
        if edge:
            account, name = edge.groups()
            if account not in user['ad_accounts']:
                raise main.MetaAPIError('asset_unavailable', 'Unsupported get request', 100, 33)
            if method == 'GET':
                if name == 'instagram_accounts':
                    return {'data': user['instagram'].get(account, [])}
                if name == 'adspixels':
                    return {'data': user['pixels'].get(account, [])}
                if name == 'campaigns':
                    return {'data': self.campaign_rows.get(account, [])}
                if name == 'insights':
                    rows = self.daily_rows if params.get('level') == 'account' else self.insight_rows
                    return {'data': rows.get(account, [])}
            self.next_id += 1
            object_id = str(self.next_id)
            self.objects[object_id] = {'account': account, 'edge': name, 'params': params,
                                       'status': params.get('status', '')}
            if name == 'campaigns':
                self.remote[object_id] = self.objects[object_id]
            return {'id': object_id}
        if re.fullmatch(r'act_\d+', path):
            if path not in user['ad_accounts']:
                raise main.MetaAPIError('asset_unavailable', 'Unsupported get request', 100, 33)
            return {'id': path, **user['ad_accounts'][path]}
        if re.fullmatch(r'\d+', path):
            item = self.remote.get(path) or self.objects.get(path)
            if not item or item['account'] not in user['ad_accounts']:
                raise main.MetaAPIError('asset_unavailable', 'Unsupported get request', 100, 33)
            if method == 'GET':
                return {'id': path, 'account_id': item['account'][4:], 'effective_status': item['status']}
            item.update({key: value for key, value in params.items()
                         if key not in ('access_token', 'appsecret_proof')})
            return {'success': True}
        raise AssertionError(f'Unexpected Graph call {method} {path}')


@pytest.fixture
def fake(monkeypatch):
    graph = FakeMeta()
    monkeypatch.setattr(main, 'PUBLIC_ORIGIN', 'https://ads-wise.com')
    monkeypatch.setattr(main, 'GOOGLE_TOKEN_ENCRYPTION_KEY', Fernet.generate_key().decode())
    monkeypatch.setattr(main, 'META_APP_ID', 'meta-app')
    monkeypatch.setattr(main, 'META_APP_SECRET', 'meta-secret')
    monkeypatch.setattr(main, 'META_LOGIN_CONFIG_ID', 'cfg-123')
    monkeypatch.setattr(main, 'meta_graph', graph)
    monkeypatch.setattr(main, 'ARK_API_KEY', 'ark-test-key')
    monkeypatch.setattr(main, 'ARK_BASE_URL', 'https://ark.ap-southeast.bytepluses.com/api/v3')
    monkeypatch.setattr(main, 'ARK_MODEL', 'seed-2-0-pro-260328')

    def seed_review(review):
        graph.seed_reviews.append(review)
        return graph.seed_verdict
    monkeypatch.setattr(main, 'seed_review_meta_change', seed_review)
    return graph


def connect_meta(client, tid, hdr, code):
    start = client.post(f'/api/workspaces/{tid}/integrations/meta/start', headers=hdr, json={})
    assert start.status_code == 200, start.text
    state = parse_qs(urlparse(start.json()['authorization_url']).query)['state'][0]
    return client.get(f'/api/integrations/meta/callback?code={code}&state={state}', follow_redirects=False)


def select(client, tid, hdr, **assets):
    return client.post(f'/api/workspaces/{tid}/integrations/meta/assets', headers=hdr, json=assets)


def ready_workspace(client, fake, code='code-A'):
    """Owner workspace A with Meta connected and Spa A's assets selected."""
    tid, hdr = session(client)
    assert 'meta=authorized' in connect_meta(client, tid, hdr, code).headers['location']
    assert select(client, tid, hdr, ad_account_id='act_111', page_id='501', instagram_account_id='601',
                  pixel_id='70100001').status_code == 200
    client.post(f'/api/workspaces/{tid}/settings', headers=hdr,
                json={'mode': 'supervised', 'budget_limit_aed': '500'}).raise_for_status()
    return tid, hdr


def pending_campaign(client, tid, hdr, **overrides):
    cid = client.post(f'/api/workspaces/{tid}/campaigns', headers=hdr, json=meta_draft(**overrides)).json()['id']
    assert client.post(f'/api/workspaces/{tid}/campaigns/{cid}/submit', headers=hdr, json={}).status_code == 200
    return cid


def member_client(tid, email, role):
    with main.connect() as db:
        uid = secrets.token_hex(12)
        db.execute('INSERT INTO users VALUES(?,?,?,?)',
                   (uid, email, main.hash_password('member-password-long-123'), main.utcnow()))
        if role:
            db.execute('INSERT INTO memberships VALUES(?,?,?)', (uid, tid, role))
    other = TestClient(main.app)
    assert other.post('/api/login', json={'email': email, 'password': 'member-password-long-123'}).status_code == 200
    return other, {'X-CSRF-Token': other.get('/api/bootstrap').json()['csrf']}


def request_change(client, tid, hdr, body):
    response = client.post(f'/api/workspaces/{tid}/integrations/meta/change-requests', headers=hdr, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def failed_checks(request):
    return {item['key'] for item in request['seed_report']['checks'] if not item['passed']}


# ---------------------------------------------------------------- OAuth -----------------------------------------

def test_oauth_start_uses_login_configuration_callback_and_throttles_attempts(client, fake):
    tid, hdr = session(client)
    first = client.post(f'/api/workspaces/{tid}/integrations/meta/start', headers=hdr, json={})
    url = urlparse(first.json()['authorization_url'])
    query = parse_qs(url.query)
    assert url.netloc == 'www.facebook.com' and url.path == f'/{main.META_GRAPH_VERSION}/dialog/oauth'
    assert query['redirect_uri'] == ['https://ads-wise.com/api/integrations/meta/callback']
    assert query['config_id'] == ['cfg-123'] and query['client_id'] == ['meta-app'] and 'scope' not in query
    for _ in range(main.META_OAUTH_STARTS_PER_WINDOW - 1):
        assert client.post(f'/api/workspaces/{tid}/integrations/meta/start', headers=hdr, json={}).status_code == 200
    blocked = client.post(f'/api/workspaces/{tid}/integrations/meta/start', headers=hdr, json={})
    assert blocked.status_code == 429 and 'Too many Meta login attempts' in blocked.json()['detail']
    assert fake.calls == []


def test_callback_encrypts_token_records_scopes_and_requires_asset_choice(client, fake):
    tid, hdr = session(client)
    response = connect_meta(client, tid, hdr, 'code-A')
    assert response.status_code == 303
    assert response.headers['location'] == 'https://ads-wise.com/app?view=accounts&meta=authorized'
    assert [call[1] for call in fake.calls] == ['oauth/access_token', 'oauth/access_token', 'debug_token']
    with main.connect() as db:
        stored = main.qrow(db, "SELECT * FROM provider_connections WHERE tenant_id=? AND provider='meta'", (tid,))
        state = main.qrow(db, 'SELECT * FROM meta_connection_state WHERE tenant_id=?', (tid,))
    assert 'token-A' not in stored['refresh_token_encrypted']
    assert main.meta_access_token(stored) == 'token-A'
    assert stored['status'] == 'authorized' and stored['customer_id'] == ''
    assert state['meta_user_id'] == 'meta-user-a' and json.loads(state['granted_scopes'])
    workspace = client.get(f'/api/workspaces/{tid}')
    assert 'token-A' not in workspace.text and 'refresh_token' not in workspace.text
    assert workspace.json()['meta']['missing_scopes'] == []
    assert 'token-A' not in client.get(f'/api/workspaces/{tid}/integrations/meta/health').text


def test_callback_rejects_reused_foreign_denied_and_sessionless_states(client, fake):
    tid, hdr = session(client)
    start = client.post(f'/api/workspaces/{tid}/integrations/meta/start', headers=hdr, json={})
    state = parse_qs(urlparse(start.json()['authorization_url']).query)['state'][0]
    other, _ = member_client(tid, 'manager@example.com', 'manager')
    foreign = other.get(f'/api/integrations/meta/callback?code=code-A&state={state}', follow_redirects=False)
    assert foreign.headers['location'].endswith('meta=error&reason=state')
    # The foreign attempt consumed the state, so the owner cannot replay it either.
    replay = client.get(f'/api/integrations/meta/callback?code=code-A&state={state}', follow_redirects=False)
    assert replay.headers['location'].endswith('meta=error&reason=state')
    start = client.post(f'/api/workspaces/{tid}/integrations/meta/start', headers=hdr, json={})
    state = parse_qs(urlparse(start.json()['authorization_url']).query)['state'][0]
    denied = client.get(f'/api/integrations/meta/callback?error=access_denied&state={state}', follow_redirects=False)
    assert denied.headers['location'].endswith('meta=error&reason=denied')
    anonymous = TestClient(main.app).get('/api/integrations/meta/callback?code=code-A&state=x', follow_redirects=False)
    assert anonymous.headers['location'].endswith('meta=error&reason=session')
    assert fake.calls == []


def test_callback_flags_missing_permissions_and_rejects_other_apps(client, fake):
    tid, hdr = session(client)
    fake.users['token-A']['scopes'] = ['ads_read', 'pages_show_list']
    response = connect_meta(client, tid, hdr, 'code-A')
    assert response.headers['location'].endswith('meta=authorized&reason=permissions')
    health = client.get(f'/api/workspaces/{tid}/integrations/meta/health').json()
    # Reading ad accounts works, which confirms the ad permissions; the Page permission is still missing.
    assert health['permissions']['missing_required'] == ['pages_read_engagement']
    assert health['overall'] == 'attention'
    other = client.post('/api/workspaces', headers=hdr, json={'name': 'Other Business'}).json()['id']
    fake.users['token-B']['app_id'] = 'someone-elses-app'
    mismatch = connect_meta(client, other, hdr, 'code-B')
    assert mismatch.headers['location'].endswith('meta=error&reason=app_mismatch')
    with main.connect() as db:
        assert main.qrow(db, "SELECT 1 AS x FROM provider_connections WHERE tenant_id=? AND provider='meta'",
                         (other,)) is None


def test_reconnect_with_different_meta_user_drops_unverified_assets(client, fake):
    tid, hdr = ready_workspace(client, fake)
    fake.codes['code-A2'] = 'token-B'  # Owner reconnects workspace A as a different Meta user.
    response = connect_meta(client, tid, hdr, 'code-A2')
    assert response.headers['location'].endswith('meta=connected')  # act_111 is still accessible
    meta = client.get(f'/api/workspaces/{tid}').json()['meta']
    assert meta['assets']['page_id'] == '' and meta['assets']['pixel_id'] == ''
    with main.connect() as db:
        kinds = {row['resource_type'] for row in main.qrows(
            db, "SELECT resource_type FROM provider_resource_bindings WHERE tenant_id=? AND provider='meta'", (tid,))}
    assert kinds == {'ad_account'}


# ---------------------------------------------------------------- Assets / isolation ----------------------------

def test_assets_are_verified_live_and_exclusive_to_one_workspace(client, fake):
    tid, hdr = session(client)
    connect_meta(client, tid, hdr, 'code-A')
    assets = client.get(f'/api/workspaces/{tid}/integrations/meta/assets?ad_account_id=act_111').json()
    assert [item['id'] for item in assets['ad_accounts']] == ['act_111']
    assert {item['id']: item['available'] for item in assets['pages']} == {'501': True, '502': False}
    assert assets['instagram_accounts'][0]['id'] == '601' and assets['pixels'][0]['id'] == '70100001'
    assert select(client, tid, hdr, ad_account_id='act_111', page_id='502').status_code == 403
    assert select(client, tid, hdr, ad_account_id='act_999').status_code == 403
    assert select(client, tid, hdr, ad_account_id='act_111', pixel_id='70200002').status_code == 403
    assert select(client, tid, hdr, ad_account_id='act_111', page_id='501', instagram_account_id='601',
                  pixel_id='70100001').status_code == 200
    workspace = client.get(f'/api/workspaces/{tid}').json()
    assert workspace['integrations']['meta']['status'] == 'connected'
    assert workspace['tracking']['meta_pixel_id'] == '70100001'

    other = client.post('/api/workspaces', headers=hdr, json={'name': 'Other Business'}).json()['id']
    connect_meta(client, other, hdr, 'code-B')
    seen = client.get(f'/api/workspaces/{other}/integrations/meta/assets?ad_account_id=act_111').json()
    assert {item['id']: item['available'] for item in seen['ad_accounts']} == {'act_111': False, 'act_222': True}
    assert {item['id']: item['available'] for item in seen['pages']} == {'501': False, '503': True}
    assert all(not item['available'] for item in seen['instagram_accounts'] + seen['pixels'])
    for attempt in ({'ad_account_id': 'act_111'}, {'ad_account_id': 'act_222', 'page_id': '501'}):
        conflict = select(client, other, hdr, **attempt)
        assert conflict.status_code == 409 and 'another workspace' in conflict.json()['detail']
    assert select(client, other, hdr, ad_account_id='act_222', page_id='503', pixel_id='70200002').status_code == 200
    taken_pixel = client.post(f'/api/workspaces/{other}/tracking', headers=hdr,
                              json={'meta_pixel_id': '70100001', 'tiktok_pixel_id': ''})
    assert taken_pixel.status_code == 409
    unverified = client.post(f'/api/workspaces/{tid}/tracking', headers=hdr,
                             json={'meta_pixel_id': '123456789', 'tiktok_pixel_id': ''})
    assert unverified.status_code == 409


def test_only_owners_can_list_or_select_assets(client, fake):
    tid, hdr = session(client)
    connect_meta(client, tid, hdr, 'code-A')
    manager, manager_hdr = member_client(tid, 'manager@example.com', 'manager')
    assert manager.get(f'/api/workspaces/{tid}/integrations/meta/assets').status_code == 403
    assert manager.post(f'/api/workspaces/{tid}/integrations/meta/assets', headers=manager_hdr,
                        json={'ad_account_id': 'act_111'}).status_code == 403
    stranger, stranger_hdr = member_client(tid, 'stranger@example.com', None)
    assert stranger.get(f'/api/workspaces/{tid}/integrations/meta/health').status_code == 404
    assert stranger.get(f'/api/workspaces/{tid}/integrations/meta/change-requests').status_code == 404


def test_disconnect_removes_token_state_bindings_and_open_requests(client, fake):
    tid, hdr = ready_workspace(client, fake)
    cid = pending_campaign(client, tid, hdr)
    request = request_change(client, tid, hdr, {'action': 'publish', 'campaign_id': cid, 'publish': launch()})
    assert request['status'] == 'awaiting_owner'
    assert client.post(f'/api/workspaces/{tid}/integrations/meta/disconnect', headers=hdr, json={}).status_code == 200
    with main.connect() as db:
        assert main.qrows(db, "SELECT * FROM provider_connections WHERE tenant_id=? AND provider='meta'", (tid,)) == []
        assert main.qrows(db, 'SELECT * FROM meta_connection_state WHERE tenant_id=?', (tid,)) == []
        assert main.qrows(db, "SELECT * FROM provider_resource_bindings WHERE tenant_id=? AND provider='meta'",
                          (tid,)) == []
        status = main.qrow(db, 'SELECT status FROM meta_change_requests WHERE id=?', (request['id'],))['status']
    assert status == 'cancelled'


# ---------------------------------------------------------------- Sync / health / errors ------------------------

def test_sync_counts_conversions_once_caches_per_workspace_and_never_leaks(client, fake):
    tid, hdr = ready_workspace(client, fake)
    synced = client.post(f'/api/workspaces/{tid}/integrations/meta/sync?range=last_30_days', headers=hdr, json={})
    assert synced.status_code == 200, synced.text
    data = synced.json()
    assert data['ad_account_id'] == 'act_111' and data['currency'] == 'AED'
    assert data['totals'] == {'impressions': 10000, 'clicks': 250, 'spend': '120.50', 'conversions': 10.0,
                              'ctr_percent': 2.5}
    assert data['campaigns'][0]['conversions_by_event'] == {'lead': 7.0, 'schedule': 3.0}
    calls = len(fake.calls)
    assert client.post(f'/api/workspaces/{tid}/integrations/meta/sync?range=last_30_days', headers=hdr,
                       json={}).json() == data
    assert len(fake.calls) == calls  # served from this workspace's fresh cache
    other = client.post('/api/workspaces', headers=hdr, json={'name': 'Other Business'}).json()['id']
    connect_meta(client, other, hdr, 'code-B')
    select(client, other, hdr, ad_account_id='act_222', page_id='503')
    assert client.get(f'/api/workspaces/{other}').json()['meta']['metrics'] is None
    other_data = client.post(f'/api/workspaces/{other}/integrations/meta/sync', headers=hdr, json={}).json()
    assert other_data['ad_account_id'] == 'act_222' and other_data['totals']['impressions'] == 0
    with main.connect() as db:  # a snapshot for a different ad account is never shown
        db.execute("UPDATE provider_snapshots SET payload=? WHERE tenant_id=? AND provider='meta'",
                   (json.dumps({**data, 'ad_account_id': 'act_222'}), tid))
    assert client.get(f'/api/workspaces/{tid}').json()['meta']['metrics'] is None


def test_meta_errors_are_classified_and_expired_tokens_require_reconnect(client, fake):
    assert main.meta_error_kind(190, 463) == 'token_expired'
    assert main.meta_error_kind(190, 460) == 'token_invalid'
    assert main.meta_error_kind(200, 0) == main.meta_error_kind(10, 0) == 'missing_permission'
    assert main.meta_error_kind(100, 33) == 'asset_unavailable'
    assert {main.meta_error_kind(code, 0) for code in (4, 17, 32, 613, 80004)} == {'rate_limited'}
    tid, hdr = ready_workspace(client, fake)
    fake.errors[('GET', 'act_111/campaigns')] = main.MetaAPIError('missing_permission', '(#200) Requires ads_read', 200)
    missing = client.post(f'/api/workspaces/{tid}/integrations/meta/sync?force=true', headers=hdr, json={})
    assert missing.status_code == 409 and 'permission' in missing.json()['detail']
    fake.errors[('GET', 'act_111/campaigns')] = main.MetaAPIError('token_expired', 'Session has expired', 190, 463)
    expired = client.post(f'/api/workspaces/{tid}/integrations/meta/sync?force=true', headers=hdr, json={})
    assert expired.status_code == 409 and 'Reconnect Meta Ads' in expired.json()['detail']
    workspace = client.get(f'/api/workspaces/{tid}').json()
    assert workspace['integrations']['meta']['status'] == 'reauth_required'
    assert client.get(f'/api/workspaces/{tid}/integrations/meta/health').json()['overall'] == 'reauth_required'


def test_live_health_reports_assets_and_is_throttled(client, fake):
    tid, hdr = ready_workspace(client, fake)
    with main.connect() as db:
        db.execute("UPDATE meta_connection_state SET last_checked_at='' WHERE tenant_id=?", (tid,))
    fake.users['token-A']['pixels']['act_111'] = []
    health = client.get(f'/api/workspaces/{tid}/integrations/meta/health?live=true').json()
    assert health['assets']['page']['available'] is True and health['assets']['pixel']['available'] is False
    assert health['overall'] == 'attention' and health['token']['days_left'] >= 49
    debug_calls = sum(call[1] == 'debug_token' for call in fake.calls)
    client.get(f'/api/workspaces/{tid}/integrations/meta/health?live=true')
    assert sum(call[1] == 'debug_token' for call in fake.calls) == debug_calls


def test_rate_limits_start_shared_cooldown_without_retrying(client, monkeypatch):
    """Uses the real Graph client with a stubbed transport to prove headers and cool-downs are honoured."""
    monkeypatch.setattr(main, 'PUBLIC_ORIGIN', 'https://ads-wise.com')
    monkeypatch.setattr(main, 'GOOGLE_TOKEN_ENCRYPTION_KEY', Fernet.generate_key().decode())
    monkeypatch.setattr(main, 'META_APP_ID', 'meta-app')
    monkeypatch.setattr(main, 'META_APP_SECRET', 'meta-secret')
    monkeypatch.setattr(main, 'META_LOGIN_CONFIG_ID', 'cfg-123')
    tid, hdr = session(client)
    sent = []

    def fake_get(url, params=None, timeout=None):
        sent.append((url, dict(params or {})))
        if len(sent) == 1:
            return httpx.Response(200, json={'data': []}, headers={'x-app-usage': json.dumps({'call_count': 10})})
        return httpx.Response(400, json={'error': {'code': 17, 'message': 'User request limit reached'}}, headers={
            'x-business-use-case-usage': json.dumps({'111': [{'type': 'ads_management', 'call_count': 100,
                                                              'estimated_time_to_regain_access': 12}]})})

    monkeypatch.setattr(main.httpx, 'get', fake_get)
    main.meta_set_scope(tid)
    main.meta_graph('GET', 'me/adaccounts', 'user-token')
    assert sent[0][1]['appsecret_proof'] == main.meta_appsecret_proof('user-token')
    with pytest.raises(main.MetaAPIError) as limited:
        main.meta_graph('GET', 'me/adaccounts', 'user-token')
    assert limited.value.kind == 'rate_limited'
    until = main.meta_cooldown_until(tid)
    assert until and until > main.utcnow()
    with pytest.raises(main.MetaAPIError) as cooling:
        main.meta_graph('GET', 'me/adaccounts', 'user-token')
    assert cooling.value.kind == 'cooling_down' and len(sent) == 2  # refused locally, Meta never called
    blocked = client.post(f'/api/workspaces/{tid}/integrations/meta/start', headers=hdr, json={})
    assert blocked.status_code == 429 and 'Retry after' in blocked.json()['detail']
    other = client.post('/api/workspaces', headers=hdr, json={'name': 'Other Business'}).json()['id']
    assert main.meta_cooldown_until(other) == ''  # another workspace's ad account is not throttled
    main.meta_set_scope('')
    main.meta_track_usage({'x-app-usage': json.dumps({'call_count': 91})}, '')
    assert main.meta_cooldown_until(other)  # app-wide usage ceiling pauses every workspace


# ---------------------------------------------------------------- Seed + owner approval -------------------------

def test_launch_needs_seed_pass_then_owner_approval_and_goes_live_active(client, fake):
    tid, hdr = ready_workspace(client, fake)
    cid = pending_campaign(client, tid, hdr)
    manager, manager_hdr = member_client(tid, 'manager@example.com', 'manager')
    request = request_change(manager, tid, manager_hdr,
                             {'action': 'publish', 'campaign_id': cid, 'publish': {**launch(), 'page_id': '999'}})
    assert request['status'] == 'awaiting_owner' and request['seed_report']['passed'] is True
    assert request['seed_report']['engine'] == main.META_SEED_ENGINE and failed_checks(request) == set()
    assert fake.posts() == []  # nothing is sent to Meta before the owner approves
    approve = f'/api/workspaces/{tid}/integrations/meta/change-requests/{request["id"]}/approve'
    assert manager.post(approve, headers=manager_hdr, json={}).status_code == 403
    approved = client.post(approve, headers=hdr, json={})
    assert approved.status_code == 200, approved.text
    assert approved.json()['status'] == 'executed' and approved.json()['result']['status'] == 'ACTIVE'
    created = {item['edge']: item['params'] for item in fake.objects.values()}
    assert created['campaigns']['status'] == created['adsets']['status'] == created['ads']['status'] == 'ACTIVE'
    story = json.loads(created['adcreatives']['object_story_spec'])
    assert story['page_id'] == '501' and story['instagram_user_id'] == '601'  # never the request's page_id
    assert json.loads(created['adsets']['promoted_object'])['pixel_id'] == '70100001'
    assert created['adsets']['daily_budget'] == '2500'
    assert all(call[1].startswith('act_111/') for call in fake.posts())
    workspace = client.get(f'/api/workspaces/{tid}').json()
    campaign = next(item for item in workspace['campaigns'] if item['id'] == cid)
    assert campaign['status'] == 'approved' and campaign['publication']['status'] == 'active'
    actions = {item['action'] for item in workspace['audit']}
    assert {'meta.change_requested', 'meta.change_executed_live', 'campaign.published_meta_active'} <= actions
    assert client.post(approve, headers=hdr, json={}).status_code == 409


def test_seed_blocks_unsafe_requests_before_the_owner_is_asked(client, fake):
    tid, hdr = ready_workspace(client, fake)
    cid = pending_campaign(client, tid, hdr)
    over = request_change(client, tid, hdr, {'action': 'publish', 'campaign_id': cid, 'publish': launch('40', 7)})
    assert over['status'] == 'seed_failed' and 'budget_upper_bounds' in failed_checks(over)
    blocked = client.post(f'/api/workspaces/{tid}/integrations/meta/change-requests/{over["id"]}/approve',
                          headers=hdr, json={})
    assert blocked.status_code == 409
    select(client, tid, hdr, ad_account_id='act_111')  # Page and Pixel removed
    incomplete = request_change(client, tid, hdr, {'action': 'publish', 'campaign_id': cid, 'publish': launch()})
    assert 'payload_complete' in failed_checks(incomplete)
    select(client, tid, hdr, ad_account_id='act_111', page_id='501', pixel_id='70100001')
    fake.users['token-A']['scopes'] = ['ads_read']
    unscoped = request_change(client, tid, hdr, {'action': 'publish', 'campaign_id': cid, 'publish': launch()})
    assert 'permissions' in failed_checks(unscoped)
    fake.users['token-A'].update({'scopes': list(main.META_REQUIRED_SCOPES), 'valid': False, 'expires_in': -60})
    expired = request_change(client, tid, hdr, {'action': 'publish', 'campaign_id': cid, 'publish': launch()})
    assert 'token_valid' in failed_checks(expired)
    fake.users['token-A'].update({'valid': True, 'expires_in': 50 * 86400})
    client.post(f'/api/workspaces/{tid}/emergency-stop', headers=hdr, json={}).raise_for_status()
    stopped = request_change(client, tid, hdr, {'action': 'publish', 'campaign_id': cid, 'publish': launch()})
    assert 'workspace_controls' in failed_checks(stopped)
    assert fake.posts() == []


def test_seed_rechecks_at_approval_and_emergency_stop_pauses_live_campaigns(client, fake):
    tid, hdr = ready_workspace(client, fake)
    cid = pending_campaign(client, tid, hdr)
    request = request_change(client, tid, hdr, {'action': 'publish', 'campaign_id': cid, 'publish': launch()})
    client.post(f'/api/workspaces/{tid}/emergency-stop', headers=hdr, json={}).raise_for_status()
    approve = f'/api/workspaces/{tid}/integrations/meta/change-requests/{request["id"]}/approve'
    late = client.post(approve, headers=hdr, json={})
    assert late.status_code == 409 and 'Seed validation failed at approval' in late.json()['detail']
    assert fake.posts() == []
    client.post(f'/api/workspaces/{tid}/resume-automation', headers=hdr, json={}).raise_for_status()
    request = request_change(client, tid, hdr, {'action': 'publish', 'campaign_id': cid, 'publish': launch()})
    live = client.post(f'/api/workspaces/{tid}/integrations/meta/change-requests/{request["id"]}/approve',
                       headers=hdr, json={}).json()
    meta_campaign = live['result']['campaign_id']
    stop = client.post(f'/api/workspaces/{tid}/emergency-stop', headers=hdr, json={}).json()
    assert stop['external_accounts_paused'] is True and stop['meta'] == {'paused': 1, 'failed': 0}
    assert fake.remote[meta_campaign]['status'] == 'PAUSED'
    assert fake.remote['8001']['status'] == 'ACTIVE'  # campaigns not launched by Adswise are left alone


def test_status_and_budget_changes_are_owner_approved_and_scoped_to_own_campaigns(client, fake):
    tid, hdr = ready_workspace(client, fake)
    cid = pending_campaign(client, tid, hdr)
    request = request_change(client, tid, hdr, {'action': 'publish', 'campaign_id': cid, 'publish': launch()})
    meta_campaign = client.post(f'/api/workspaces/{tid}/integrations/meta/change-requests/{request["id"]}/approve',
                                headers=hdr, json={}).json()['result']['campaign_id']
    enable_external = request_change(client, tid, hdr, {'action': 'set_status', 'target_id': '8001', 'status': 'ACTIVE'})
    assert 'managed_campaign' in failed_checks(enable_external)
    pause_external = request_change(client, tid, hdr, {'action': 'set_status', 'target_id': '8001', 'status': 'PAUSED'})
    assert pause_external['status'] == 'awaiting_owner'
    foreign = request_change(client, tid, hdr, {'action': 'set_status', 'target_id': '8002', 'status': 'PAUSED'})
    assert foreign['status'] == 'seed_failed'
    too_high = request_change(client, tid, hdr, {'action': 'set_budget', 'target_id': meta_campaign,
                                                 'daily_budget_aed': '30'})
    assert 'budget_upper_bounds' in failed_checks(too_high)
    budget = request_change(client, tid, hdr, {'action': 'set_budget', 'target_id': meta_campaign,
                                               'daily_budget_aed': '20'})
    assert budget['status'] == 'awaiting_owner'
    done = client.post(f'/api/workspaces/{tid}/integrations/meta/change-requests/{budget["id"]}/approve',
                       headers=hdr, json={})
    assert done.status_code == 200 and done.json()['result']['daily_budget_aed'] == '20.00'
    adset = next(item for item in fake.objects.values() if item['edge'] == 'adsets')
    assert adset['daily_budget'] == '2000'
    rejected = client.post(f'/api/workspaces/{tid}/integrations/meta/change-requests/{pause_external["id"]}/reject',
                           headers=hdr, json={})
    assert rejected.status_code == 200 and fake.remote['8001']['status'] == 'ACTIVE'


def test_change_requests_cannot_cross_workspaces(client, fake):
    tid, hdr = ready_workspace(client, fake)
    cid = pending_campaign(client, tid, hdr)
    request = request_change(client, tid, hdr, {'action': 'publish', 'campaign_id': cid, 'publish': launch()})
    other = client.post('/api/workspaces', headers=hdr, json={'name': 'Other Business'}).json()['id']
    connect_meta(client, other, hdr, 'code-B')
    select(client, other, hdr, ad_account_id='act_222', page_id='503', pixel_id='70200002')
    client.post(f'/api/workspaces/{other}/settings', headers=hdr,
                json={'mode': 'supervised', 'budget_limit_aed': '500'}).raise_for_status()
    cross = client.post(f'/api/workspaces/{other}/integrations/meta/change-requests/{request["id"]}/approve',
                        headers=hdr, json={})
    assert cross.status_code == 404
    assert client.get(f'/api/workspaces/{other}/integrations/meta/change-requests').json()['requests'] == []
    stolen = request_change(client, other, hdr, {'action': 'publish', 'campaign_id': cid, 'publish': launch()})
    assert 'campaign' in failed_checks(stolen)
    assert fake.posts() == []


def test_legacy_publish_route_only_creates_a_seed_validated_request(client, fake):
    tid, hdr = ready_workspace(client, fake)
    cid = pending_campaign(client, tid, hdr)
    response = client.post(f'/api/workspaces/{tid}/campaigns/{cid}/publish/meta', headers=hdr, json=launch())
    assert response.status_code == 200 and response.json()['status'] == 'awaiting_owner'
    assert fake.posts() == []


# ---------------------------------------------------------------- Seed AI review ------------------------------

def test_seed_ai_review_is_obligatory_fail_closed_and_reused_at_approval(client, fake, monkeypatch):
    tid, hdr = ready_workspace(client, fake)
    cid = pending_campaign(client, tid, hdr)
    fake.seed_verdict = {'decision': 'fail', 'summary': 'Health claim.', 'issues': ['"Cures back pain" is a medical claim']}
    rejected = request_change(client, tid, hdr, {'action': 'publish', 'campaign_id': cid, 'publish': launch()})
    assert rejected['status'] == 'seed_failed' and failed_checks(rejected) == {'seed_ai_review'}
    assert 'medical claim' in next(item['detail'] for item in rejected['seed_report']['checks']
                                   if item['key'] == 'seed_ai_review')
    review = fake.seed_reviews[-1]
    assert review['creative']['headline'] == 'Relax at Be Relax' and 'token' not in json.dumps(review).lower()
    fake.seed_verdict = {'decision': 'pass', 'summary': 'ok', 'issues': []}
    request = request_change(client, tid, hdr, {'action': 'publish', 'campaign_id': cid,
                                                'publish': {**launch(), 'headline': 'Unwind at Be Relax'}})
    assert request['status'] == 'awaiting_owner'
    reviews = len(fake.seed_reviews)
    approved = client.post(f'/api/workspaces/{tid}/integrations/meta/change-requests/{request["id"]}/approve',
                           headers=hdr, json={})
    assert approved.status_code == 200 and len(fake.seed_reviews) == reviews  # verdict reused, rules re-run
    monkeypatch.setattr(main, 'ARK_API_KEY', '')
    unconfigured = request_change(client, tid, hdr, {'action': 'set_budget', 'target_id': approved.json()['result']['campaign_id'],
                                                     'daily_budget_aed': '20'})
    assert unconfigured['status'] == 'seed_failed' and failed_checks(unconfigured) == {'seed_ai_review'}
    pause = request_change(client, tid, hdr, {'action': 'set_status', 'target_id': '8001', 'status': 'PAUSED'})
    assert pause['status'] == 'awaiting_owner'  # pausing reduces risk and never depends on the AI
    assert all(item['key'] != 'seed_ai_review' for item in pause['seed_report']['checks'])


def test_seed_review_client_sends_server_side_key_and_validates_answer(monkeypatch):
    monkeypatch.setattr(main, 'ARK_API_KEY', 'ark-test-key')
    monkeypatch.setattr(main, 'ARK_BASE_URL', 'https://ark.ap-southeast.bytepluses.com/api/v3')
    monkeypatch.setattr(main, 'ARK_MODEL', 'seed-2-0-pro-260328')
    sent = {}

    def fake_post(url, **kwargs):
        sent.update(url=url, **kwargs)
        return httpx.Response(200, request=httpx.Request('POST', url), json={'choices': [{'message': {
            'content': '```json\n{"decision":"pass","summary":"fine","issues":[]}\n```'}}]})

    monkeypatch.setattr(main.httpx, 'post', fake_post)
    assert main.seed_review_meta_change({'action': 'publish'})['decision'] == 'pass'
    assert sent['url'] == 'https://ark.ap-southeast.bytepluses.com/api/v3/chat/completions'
    assert sent['headers']['Authorization'] == 'Bearer ark-test-key' and sent['json']['model'] == 'seed-2-0-pro-260328'
    monkeypatch.setattr(main.httpx, 'post', lambda url, **kwargs: httpx.Response(
        200, request=httpx.Request('POST', url), json={'choices': [{'message': {'content': '{"decision":"maybe"}'}}]}))
    with pytest.raises(ValueError):
        main.seed_review_meta_change({'action': 'publish'})


def test_business_management_is_not_required_or_requested(client, fake):
    assert 'business_management' not in main.META_REQUIRED_SCOPES
    assert fake.users['token-A']['scopes'] == list(main.META_REQUIRED_SCOPES)  # granted without it
    tid, hdr = ready_workspace(client, fake)
    adaccount_fields = [call[3]['fields'] for call in fake.calls if call[1] == 'me/adaccounts']
    assert adaccount_fields and all('business' not in fields for fields in adaccount_fields)
    cid = pending_campaign(client, tid, hdr)
    request = request_change(client, tid, hdr, {'action': 'publish', 'campaign_id': cid, 'publish': launch()})
    assert request['status'] == 'awaiting_owner' and failed_checks(request) == set()
    health = client.get(f'/api/workspaces/{tid}/integrations/meta/health').json()
    assert health['permissions']['missing_required'] == []


# ---------------------------------------------------------------- Permission detection (debug_token) ----------

ARKS_ACCOUNT = 'act_2005981653917424'


def arks_system_user(fake, granular=True, ads_access=None):
    """Login for Business system-user token: business permissions only in granular_scopes, Pages without tasks."""
    user = {'user_id': 'system-user-arks', 'valid': True, 'expires_at': 0,  # 0 = never expires (system user)
            'scopes': ['pages_read_engagement', 'pages_show_list', 'public_profile'],
            'granular': ([{'scope': 'ads_read', 'target_ids': [ARKS_ACCOUNT[4:]]},
                          {'scope': 'ads_management', 'target_ids': [ARKS_ACCOUNT[4:]]},
                          {'scope': 'pages_show_list', 'target_ids': ['9001', '9002']}] if granular else []),
            'ad_accounts': {ARKS_ACCOUNT: {'name': 'ARKS investment Holding LTD', 'currency': 'AED',
                                           'timezone_name': 'Asia/Dubai', 'account_status': 1}},
            'pages': [{'id': '9001', 'name': 'ARKS Investment Holding Ltd'}, {'id': '9002', 'name': 'Trainsyou.com'}],
            'instagram': {ARKS_ACCOUNT: []}, 'pixels': {ARKS_ACCOUNT: []}}
    if ads_access is not None:
        user['ads_access'] = ads_access
    fake.users['token-ARKS'] = user
    fake.codes['code-ARKS'] = 'token-ARKS'


def live_health(client, tid):
    with main.connect() as db:
        db.execute("UPDATE meta_connection_state SET last_checked_at='' WHERE tenant_id=?", (tid,))
    return client.get(f'/api/workspaces/{tid}/integrations/meta/health?live=true').json()


def test_full_debug_token_scopes_report_nothing_missing(client, fake):
    tid, hdr = session(client)
    assert fake.users['token-A']['scopes'] == ['ads_read', 'ads_management', 'pages_show_list', 'pages_read_engagement']
    assert connect_meta(client, tid, hdr, 'code-A').headers['location'].endswith('meta=authorized')
    assert not any(call[1] == 'me/adaccounts' for call in fake.calls)  # no extra Meta call needed
    health = live_health(client, tid)
    assert health['permissions']['missing_required'] == []
    assert set(health['permissions']) == {'required', 'optional', 'granted', 'missing_required'}  # shape unchanged
    assert health['permissions']['required'] == ['ads_read', 'ads_management', 'pages_show_list', 'pages_read_engagement']
    assert health['permissions']['optional'] == ['pages_manage_ads']


def test_system_user_token_ad_permissions_come_from_granular_scopes(client, fake):
    """Regression: ads_read/ads_management were reported missing for Login for Business system-user tokens."""
    tid, hdr = session(client)
    arks_system_user(fake)
    response = connect_meta(client, tid, hdr, 'code-ARKS')
    assert response.headers['location'].endswith('meta=authorized')  # no reason=permissions
    health = live_health(client, tid)
    assert health['permissions']['missing_required'] == []
    assert {'ads_read', 'ads_management', 'pages_show_list', 'pages_read_engagement'} <= set(health['permissions']['granted'])
    assert 'business_management' not in health['permissions']['required']
    assert health['token']['never_expires'] is True
    assert client.get(f'/api/workspaces/{tid}').json()['meta']['missing_scopes'] == []


def test_ad_access_check_confirms_permissions_debug_token_does_not_list(client, fake):
    tid, hdr = session(client)
    arks_system_user(fake, granular=False, ads_access=True)
    response = connect_meta(client, tid, hdr, 'code-ARKS')
    assert response.headers['location'].endswith('meta=authorized')
    check = next(call for call in fake.calls if call[1] == 'me/adaccounts')
    assert check[3]['fields'] == 'id,name,account_status'
    assert len([call for call in fake.calls if call[0] == 'GET']) <= 4  # callback stays within four Meta calls
    assert live_health(client, tid)['permissions']['missing_required'] == []


def test_token_missing_ads_read_is_reported_missing(client, fake):
    tid, hdr = session(client)
    arks_system_user(fake, granular=False)  # Page permissions only and no working ad account access
    response = connect_meta(client, tid, hdr, 'code-ARKS')
    assert response.headers['location'].endswith('meta=authorized&reason=permissions')
    health = live_health(client, tid)
    assert health['permissions']['missing_required'] == ['ads_read', 'ads_management']
    assert health['overall'] == 'attention'


def test_choose_assets_lists_arks_ad_account_and_both_pages(client, fake):
    tid, hdr = session(client)
    arks_system_user(fake)
    connect_meta(client, tid, hdr, 'code-ARKS')
    assets = client.get(f'/api/workspaces/{tid}/integrations/meta/assets').json()
    assert [(item['id'], item['name'], item['available']) for item in assets['ad_accounts']] == [
        (ARKS_ACCOUNT, 'ARKS investment Holding LTD', True)]
    assert {(item['name'], item['available']) for item in assets['pages']} == {
        ('ARKS Investment Holding Ltd', True), ('Trainsyou.com', True)}
    saved = select(client, tid, hdr, ad_account_id=ARKS_ACCOUNT, page_id='9002')
    assert saved.status_code == 200 and saved.json()['page']['name'] == 'Trainsyou.com'
    serialized = json.dumps(assets) + client.get(f'/api/workspaces/{tid}').text
    assert 'token-ARKS' not in serialized and main.META_APP_SECRET not in serialized


def test_pages_with_tasks_but_no_advertise_role_stay_blocked(client, fake):
    tid, hdr = session(client)
    connect_meta(client, tid, hdr, 'code-A')
    pages = client.get(f'/api/workspaces/{tid}/integrations/meta/assets?ad_account_id=act_111').json()['pages']
    assert {item['id']: item['available'] for item in pages} == {'501': True, '502': False}


# ---------------------------------------------------------------- Deploy indicator and permission diagnostics ----

def permission_logs(capsys, stage):
    lines = [json.loads(line) for line in capsys.readouterr().err.splitlines() if line.startswith('{')]
    return [line for line in lines if line.get('event') == 'meta.permission_check' and line.get('stage') == stage]


def test_health_reports_deployed_commit(client, monkeypatch):
    for name in ('VERCEL_GIT_COMMIT_SHA', 'SOURCE_VERSION', 'GITHUB_SHA', 'VERCEL_GIT_COMMIT_REF', 'VERCEL_ENV'):
        monkeypatch.delenv(name, raising=False)
    assert client.get('/api/health').json() == {'status': 'ok', 'service': 'spa-ads-agent', 'commit': 'unknown',
                                                 'branch': '', 'environment': ''}
    monkeypatch.setenv('VERCEL_GIT_COMMIT_SHA', '731b84d5e92b4981c5dee8b114bf877a2d97e6ff')
    monkeypatch.setenv('VERCEL_GIT_COMMIT_REF', 'main')
    monkeypatch.setenv('VERCEL_ENV', 'production')
    assert client.get('/api/health').json() == {'status': 'ok', 'service': 'spa-ads-agent', 'commit': '731b84d',
                                                 'branch': 'main', 'environment': 'production'}


def test_reconnect_logs_permission_source_scopes_and_ad_check_without_secrets(client, fake, capsys):
    tid, hdr = session(client)
    arks_system_user(fake, granular=False, ads_access=False)
    capsys.readouterr()
    connect_meta(client, tid, hdr, 'code-ARKS')
    output = capsys.readouterr().err
    [log] = [json.loads(line) for line in output.splitlines() if '"stage":"oauth_callback"' in line]
    assert log['permission_source'] == 'debug_token'
    assert log['debug_scopes'] == ['pages_read_engagement', 'pages_show_list', 'public_profile']
    assert log['debug_granular_scopes'] == []
    assert log['ad_access_check'] == 'me_adaccounts_failed:missing_permission:200:0'
    assert log['missing_required'] == ['ads_read', 'ads_management'] and log['redirect_reason'] == 'permissions'
    for secret in ('token-ARKS', 'short-token-ARKS', main.META_APP_SECRET, 'code-ARKS'):
        assert secret not in output
    audit = next(item for item in client.get(f'/api/workspaces/{tid}').json()['audit']
                 if item['action'] == 'integration.meta_authorized')
    assert audit['detail']['permission_diagnostics']['ad_access_check'] == log['ad_access_check']
    health = client.get(f'/api/workspaces/{tid}/integrations/meta/health').json()
    assert health['last_error']['kind'] == 'missing_permission' and 'Requires ads_read' in health['last_error']['message']


def test_reconnect_logs_which_source_granted_the_ad_permissions(client, fake, capsys):
    tid, hdr = session(client)
    arks_system_user(fake)  # ad permissions listed in granular_scopes
    capsys.readouterr()
    connect_meta(client, tid, hdr, 'code-ARKS')
    [log] = permission_logs(capsys, 'oauth_callback')
    assert log['debug_granular_scopes'] == ['ads_management', 'ads_read', 'pages_show_list']
    assert (log['permission_source'], log['ad_access_check'], log['missing_required']) == ('debug_token', 'not_needed', [])
    other = client.post('/api/workspaces', headers=hdr, json={'name': 'Other Business'}).json()['id']
    arks_system_user(fake, granular=False, ads_access=True)
    fake.codes['code-ARKS-2'] = 'token-ARKS'
    connect_meta(client, other, hdr, 'code-ARKS-2')
    [log] = permission_logs(capsys, 'oauth_callback')
    assert (log['permission_source'], log['ad_access_check'], log['missing_required']) == (
        'debug_token+me_adaccounts', 'me_adaccounts_ok', [])


def test_unfinished_permission_check_is_rechecked_not_served_from_cache(client, fake, capsys):
    tid, hdr = session(client)
    arks_system_user(fake, granular=False, ads_access=True)
    fake.errors[('GET', 'me/adaccounts')] = main.MetaAPIError('rate_limited', 'User request limit reached', 17)
    response = connect_meta(client, tid, hdr, 'code-ARKS')
    assert response.headers['location'].endswith('meta=authorized&reason=rate_limited')
    assert main.meta_state(tid)['last_checked_at'] == ''
    del fake.errors[('GET', 'me/adaccounts')]
    debug_calls = sum(call[1] == 'debug_token' for call in fake.calls)
    capsys.readouterr()
    health = client.get(f'/api/workspaces/{tid}/integrations/meta/health?live=true').json()
    assert sum(call[1] == 'debug_token' for call in fake.calls) == debug_calls + 1  # asked Meta again immediately
    assert health['permissions']['missing_required'] == []
    [log] = permission_logs(capsys, 'health_live')
    assert log['ad_access_check'] == 'me_adaccounts_ok'
    client.get(f'/api/workspaces/{tid}/integrations/meta/health?live=true')
    [skipped] = permission_logs(capsys, 'health_live_skipped')
    assert skipped['reason'] == 'checked_under_60s_ago' and 'ads_read' in skipped['stored_granted']
