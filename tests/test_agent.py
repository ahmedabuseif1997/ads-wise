import hashlib
import os
import secrets
from urllib.parse import parse_qs, urlparse

os.environ.setdefault('ADMIN_EMAIL','owner@example.com')
os.environ.setdefault('ADMIN_PASSWORD','really-long-integration-password-123')
os.environ.setdefault('COOKIE_SECURE','false')

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from app import main


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'DB_PATH',tmp_path/'adsagent.db')
    monkeypatch.setattr(main,'AI_API_KEY','')
    monkeypatch.setattr(main,'AI_BASE_URL','')
    monkeypatch.setattr(main,'MINIMAX_API_KEY','')
    monkeypatch.setattr(main,'META_APP_ID','')
    monkeypatch.setattr(main,'META_APP_SECRET','')
    monkeypatch.setattr(main,'META_LOGIN_CONFIG_ID','')
    monkeypatch.setattr(main,'TIKTOK_APP_ID','')
    monkeypatch.setattr(main,'TIKTOK_APP_SECRET','')
    monkeypatch.setattr(main,'TIKTOK_AUTHORIZATION_URL','')
    monkeypatch.setattr(main,'GOOGLE_GROWTH_CLIENT_ID','')
    monkeypatch.setattr(main,'GOOGLE_GROWTH_CLIENT_SECRET','')
    main._LOGIN_ATTEMPTS.clear()
    main.init_db()
    with TestClient(main.app) as c:
        yield c


def session(client):
    r=client.post('/api/login',json={'email':os.environ['ADMIN_EMAIL'],'password':os.environ['ADMIN_PASSWORD']})
    assert r.status_code == 200
    boot=client.get('/api/bootstrap').json()
    return boot['tenants'][0]['id'], {'X-CSRF-Token':boot['csrf']}


def draft():
    return {'name':'Wellness weekends','provider':'meta','objective':'bookings',
            'service':'Spa Massage','brief':'Promote our sessions','copy':'Take time to unwind.',
            'landing_url':'https://example.com/book','budget_aed':'200.00',
            'audience_location':'Abu Dhabi, UAE','audience_age_min':25,'audience_age_max':55,
            'audience_gender':'all','audience_interests':'massage, wellness',
            'placements':'Instagram and Facebook feeds',
            'image_urls':'https://cdn.example.com/massage.jpg','call_to_action':'BOOK_NOW'}


def test_health_and_static(client):
    assert client.get('/api/health').json()['status']=='ok'
    homepage=client.get('/')
    assert homepage.status_code==200
    assert 'Every signal. One clear move.' in homepage.text
    assert 'Clearer campaigns.' in homepage.text
    assert 'info@ads-wise.com' in homepage.text
    assert 'data-theme="dark"' in homepage.text
    cinematic_js=client.get('/assets/cinematic.js')
    assert cinematic_js.status_code==200
    assert 'sg("adw2_theme")||"dark"' in cinematic_js.text
    assert 'const LOGIN_URL = "/app"' in cinematic_js.text
    assert client.get('/app').status_code==200
    assert client.get('/signup').status_code==200
    assert client.get('/reset-password').status_code==200
    assert client.get('/privacy').status_code==200
    assert client.get('/terms').status_code==200
    assert client.get('/data-deletion').status_code==200
    assert client.get('/assets/style.css').status_code==200
    assert client.get('/assets/analytics.css').status_code==200
    assert client.get('/assets/app.js').status_code==200
    assert client.get('/assets/workspace-isolation.js').status_code==200
    assert client.get('/assets/landing.css').status_code==200
    assert client.get('/assets/cinematic.css').status_code==200
    assert client.get('/assets/landing-footer.css').status_code==200
    assert client.get('/assets/brand-palette.css').status_code==200
    assert client.get('/assets/landing.js').status_code==200
    analytics_tag=client.get('/assets/analytics-tag.js')
    assert analytics_tag.status_code==200
    assert 'G-4F7P3370QN' in analytics_tag.text
    assert 'G-4F7P3370QN' in homepage.text
    assert client.get('/assets/responsive-fixes.css').status_code==200
    assert client.get('/assets/dashboard-redesign.css').status_code==200
    assert client.get('/assets/adwise-mark.svg').status_code==200
    assert client.get('/assets/adwise-ad-mark-v2.png').status_code==200
    assert client.get('/assets/adwise-icon-192.png').status_code==200
    assert client.get('/assets/adwise-icon-512.png').status_code==200
    assert '/assets/adwise-ad-mark-v2.png' in client.get('/').text
    assert client.get('/manifest.webmanifest').status_code==200
    assert client.get('/service-worker.js').status_code==200
    assert client.get('/assets/signup.js').status_code==200
    assert client.get('/assets/reset-password.js').status_code==200
    assert client.get('/assets/privacy.css').status_code==200
    assert "frame-ancestors 'none'" in client.get('/').headers['content-security-policy']
    assert 'Forgot password?' in client.get('/app').text


def test_login_required(client):
    assert client.get('/api/bootstrap').status_code==401
    assert client.get('/api/workspaces/bad').status_code==401
    assert client.post('/api/login',json={'email':'owner@example.com','password':'not-it'}).status_code==401


def test_password_reset_and_successful_logins_do_not_lock(client, monkeypatch):
    sent = []
    monkeypatch.setattr(main, 'send_registration_email',
                        lambda to, subject, text: sent.append((to, subject, text)) or True)
    unknown = client.post('/api/forgot-password', json={'email': 'missing@example.com'})
    known = client.post('/api/forgot-password', json={'email': os.environ['ADMIN_EMAIL']})
    assert unknown.status_code == known.status_code == 200
    assert unknown.json()['message'] == known.json()['message']
    assert len(sent) == 1 and sent[0][0] == os.environ['ADMIN_EMAIL']
    token = parse_qs(urlparse(sent[0][2].splitlines()[2]).query)['token'][0]
    new_password = 'new-secure-owner-password-456'
    reset = client.post('/api/reset-password', json={'token': token, 'password': new_password})
    assert reset.status_code == 200
    assert client.post('/api/reset-password', json={'token': token, 'password': new_password}).status_code == 400
    assert client.post('/api/login', json={'email': os.environ['ADMIN_EMAIL'],
                                            'password': os.environ['ADMIN_PASSWORD']}).status_code == 401
    for _ in range(10):
        assert client.post('/api/login', json={'email': os.environ['ADMIN_EMAIL'],
                                                'password': new_password}).status_code == 200


def test_csrf_and_authenticated_session(client):
    tid, hdr=session(client)
    assert client.post('/api/workspaces',json={'name':'New Spa'}).status_code==403
    assert client.get(f'/api/workspaces/{tid}').status_code==200
    assert client.post('/api/workspaces',headers=hdr,json={'name':'New Spa'}).status_code==200
    assert len(client.get('/api/bootstrap').json()['tenants'])==2


def test_tenant_tracking_configuration(client):
    tid, headers = session(client)
    initial = client.get(f'/api/workspaces/{tid}').json()
    assert initial['tracking']['meta_pixel_id'] == ''
    saved = client.post(f'/api/workspaces/{tid}/tracking', headers=headers, json={
        'meta_pixel_id': '123456789012345', 'tiktok_pixel_id': 'CABC12345',
        'lead_event': 'Lead', 'booking_event': 'Schedule'})
    assert saved.status_code == 200
    workspace = client.get(f'/api/workspaces/{tid}').json()
    assert workspace['tracking']['meta_pixel_id'] == '123456789012345'
    assert workspace['tracking']['tiktok_pixel_id'] == 'CABC12345'
    assert workspace['tracking']['events']['booking'] == 'Schedule'
    assert client.post(f'/api/workspaces/{tid}/tracking', headers=headers, json={
        'meta_pixel_id': 'not-a-number', 'tiktok_pixel_id': ''}).status_code == 422


def test_tenant_tracking_script_is_scoped_and_contains_no_secrets(client):
    tid, headers = session(client)
    assert client.get(f'/tracking/{tid}.js').status_code == 404
    client.post(f'/api/workspaces/{tid}/tracking', headers=headers, json={
        'meta_pixel_id': '123456789012345', 'tiktok_pixel_id': 'CABC12345',
        'lead_event': 'Lead', 'booking_event': 'Schedule'}).raise_for_status()
    response = client.get(f'/tracking/{tid}.js')
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('application/javascript')
    assert '123456789012345' in response.text and 'CABC12345' in response.text
    assert 'adwiseTrack' in response.text and 'PageView' in response.text
    assert 'APP_SECRET' not in response.text and 'refresh_token' not in response.text
    assert client.get('/tracking/not-a-workspace.js').status_code == 404


def test_sitemap_submission_is_limited_to_connected_tenant_property(client, monkeypatch):
    class PutResponse:
        status_code = 200

        def raise_for_status(self):
            return None

    tid, headers = session(client)
    monkeypatch.setattr(main, 'GOOGLE_TOKEN_ENCRYPTION_KEY', Fernet.generate_key().decode())
    main.save_provider_connection(tid, 'google_growth', 'refresh-token', 'accounts/1', 'Business Profile')
    with main.connect() as db:
        db.execute('INSERT INTO provider_snapshots(tenant_id,provider,payload,updated_at) VALUES(?,?,?,?)',
                   (tid, 'google_growth', '{"search_console_sites":[{"siteUrl":"https://example.com/"}]}',
                    main.utcnow()))
    monkeypatch.setattr(main, 'google_growth_access_token', lambda connection: 'access-token')
    calls = []
    def fake_put(url, **kwargs):
        calls.append((url, kwargs))
        return PutResponse()
    monkeypatch.setattr(main.httpx, 'put', fake_put)
    result = client.post(f'/api/workspaces/{tid}/integrations/google-growth/sitemaps', headers=headers,
                         json={'site_url': 'https://example.com/',
                               'sitemap_url': 'https://example.com/sitemap.xml'})
    assert result.status_code == 200 and result.json()['submitted'] is True
    assert len(calls) == 1 and calls[0][1]['headers']['Authorization'] == 'Bearer access-token'
    denied = client.post(f'/api/workspaces/{tid}/integrations/google-growth/sitemaps', headers=headers,
                         json={'site_url': 'https://other.example/',
                               'sitemap_url': 'https://other.example/sitemap.xml'})
    assert denied.status_code == 409


def test_tenant_registration_and_team_invitation(client):
    registration = client.post('/api/register', json={
        'email': 'newtenant@example.com', 'password': 'new-tenant-password-12345',
        'business_name': 'New Wellness Tenant'})
    assert registration.status_code == 200 and registration.json()['status'] == 'pending'
    _, admin_headers = session(client)
    overview = client.get('/api/admin/overview').json()
    request_id = next(x['id'] for x in overview['registration_requests']
                      if x['email'] == 'newtenant@example.com')
    approved = client.post(f'/api/admin/registration-requests/{request_id}/approve',
                           headers=admin_headers, json={})
    assert approved.status_code == 200
    client.post('/api/logout', headers=admin_headers, json={})
    login = client.post('/api/login', json={'email': 'newtenant@example.com',
                                             'password': 'new-tenant-password-12345'})
    assert login.status_code == 200
    boot = client.get('/api/bootstrap').json()
    assert boot['tenants'][0]['name'] == 'New Wellness Tenant'
    tid, csrf = boot['tenants'][0]['id'], {'X-CSRF-Token': boot['csrf']}
    invitation = client.post(f'/api/workspaces/{tid}/invitations', headers=csrf,
                             json={'email': 'manager@example.com', 'role': 'manager'})
    assert invitation.status_code == 200
    invite_token = parse_qs(urlparse(invitation.json()['invite_url']).query)['invite'][0]
    client.post('/api/logout', headers=csrf, json={})
    accepted = client.post('/api/register', json={
        'email': 'manager@example.com', 'password': 'manager-password-12345',
        'business_name': '', 'invite_token': invite_token})
    assert accepted.status_code == 200 and accepted.json()['tenant_id'] == tid
    manager_boot = client.get('/api/bootstrap').json()
    manager_headers = {'X-CSRF-Token': manager_boot['csrf']}
    assert manager_boot['tenants'][0]['role'] == 'manager'
    campaign = client.post(f'/api/workspaces/{tid}/campaigns', headers=manager_headers, json=draft())
    assert campaign.status_code == 200
    assert client.post(f"/api/workspaces/{tid}/campaigns/{campaign.json()['id']}/approve",
                       headers=manager_headers, json={}).status_code == 403


def test_workspace_isolation(client):
    _, hdr=session(client)
    # Create another user without membership and give them an authorized session.
    with main.connect() as db:
        uid=secrets.token_hex(12)
        db.execute('INSERT INTO users VALUES(?,?,?,?)',
                   (uid,'other@example.com',main.hash_password('second-owner-password-long'),main.utcnow()))
    client.post('/api/logout',json={},headers=hdr)
    assert client.post('/api/login',json={'email':'other@example.com','password':'second-owner-password-long'}).status_code==200
    b=client.get('/api/bootstrap').json()
    assert b['tenants']==[]
    with main.connect() as db:
        tenant=main.qrow(db,'SELECT id FROM tenants LIMIT 1')['id']
    assert client.get(f'/api/workspaces/{tenant}').status_code==404
    assert client.post(f'/api/workspaces/{tenant}/campaigns',json=draft(),
                       headers={'X-CSRF-Token':b['csrf']}).status_code==404


def test_super_admin_can_access_and_manage_every_tenant(client):
    tid, headers = session(client)
    with main.connect() as db:
        other_tid = secrets.token_hex(12)
        db.execute('INSERT INTO tenants VALUES(?,?,?)', (other_tid, 'Unassigned Tenant', main.utcnow()))
        db.execute('INSERT INTO tenant_settings(tenant_id,mode,budget_limit_fils,stopped) VALUES(?,?,?,?)',
                   (other_tid, 'manual', 0, 0))
    boot = client.get('/api/bootstrap').json()
    assert boot['super_admin'] is True
    assert {tenant['id'] for tenant in boot['tenants']} == {tid, other_tid}
    workspace = client.get(f'/api/workspaces/{other_tid}')
    assert workspace.status_code == 200
    assert workspace.json()['current_role'] == 'owner'
    updated = client.post(f'/api/workspaces/{other_tid}/settings', headers=headers,
                          json={'mode':'supervised','budget_limit_aed':'500'})
    assert updated.status_code == 200


def test_super_admin_health_controls_and_developer_queue(client,monkeypatch):
    tenant_id,headers=session(client)
    assert client.get('/admin').status_code==200
    legacy=client.get('/super-admin',follow_redirects=False)
    assert legacy.status_code==308 and legacy.headers['location']=='/admin'
    overview=client.get('/api/admin/overview')
    assert overview.status_code==200
    payload=overview.json()
    assert payload['platform']['app_name']=='Ads-Wise — AI Marketing OS'
    assert payload['health']['database']=='healthy'
    assert {item['name'] for item in payload['health']['apis']} >= {
        'Google Ads API','Meta Marketing API','TikTok Marketing API','Resend Email API'}

    paused=client.post(f'/api/admin/tenants/{tenant_id}/controls',headers=headers,
                       json={'ai_paused':True})
    assert paused.status_code==200
    plan=client.post(f'/api/workspaces/{tenant_id}/agent/plan',headers=headers,json={
        'service':'Massage','provider':'meta','objective':'bookings','budget_aed':'100',
        'brief':'Create a booking campaign'})
    assert plan.status_code==423
    global_pause=client.post('/api/admin/ai-control',headers=headers,json={'paused':True})
    assert global_pause.status_code==200 and global_pause.json()['paused'] is True
    queued=client.post('/api/admin/developer-agent-requests',headers=headers,json={
        'agent':'codex','instructions':'Add a tested accessibility improvement to the admin dashboard.'})
    assert queued.status_code==200 and queued.json()['status']=='awaiting_runner'
    assert client.post('/mcp/developer',json={'jsonrpc':'2.0','id':1,'method':'tools/list'}).status_code==401
    monkeypatch.setattr(main,'MCP_AGENT_TOKEN','test-mcp-token')
    mcp_headers={'Authorization':'Bearer test-mcp-token'}
    listed=client.post('/mcp/developer',headers=mcp_headers,json={
        'jsonrpc':'2.0','id':2,'method':'tools/call','params':{
            'name':'list_development_tasks','arguments':{'agent':'codex'}}})
    assert listed.status_code==200 and queued.json()['id'] in listed.json()['result']['content'][0]['text']
    updated=client.post('/mcp/developer',headers=mcp_headers,json={
        'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'update_development_task','arguments':{
            'id':queued.json()['id'],'status':'needs_approval','branch_name':'codex/admin-a11y',
            'pull_request_url':'https://github.com/ahmedabuseif1997/ads-wise/pull/123'}}})
    assert updated.status_code==200
    refreshed=client.get('/api/admin/overview').json()
    assert refreshed['health']['global_ai_paused'] is True
    assert refreshed['agent_requests'][0]['agent']=='codex'
    with main.connect() as db:
        member_id=secrets.token_hex(12)
        db.execute('INSERT INTO users VALUES(?,?,?,?)',
                   (member_id,'paused@example.com',main.hash_password('paused-tenant-password-123'),main.utcnow()))
        db.execute('INSERT INTO memberships VALUES(?,?,?)',(member_id,tenant_id,'owner'))
    assert client.post(f'/api/admin/tenants/{tenant_id}/controls',headers=headers,
                       json={'tenant_paused':True}).status_code==200
    client.post('/api/logout',headers=headers,json={})
    assert client.post('/api/login',json={'email':'paused@example.com',
                                           'password':'paused-tenant-password-123'}).status_code==200
    assert client.get(f'/api/workspaces/{tenant_id}').status_code==423


def test_approval_budget_and_audit(client):
    tid,hdr=session(client)
    r=client.post(f'/api/workspaces/{tid}/campaigns',json=draft(),headers=hdr)
    assert r.status_code==200
    cid=r.json()['id']
    assert client.post(f'/api/workspaces/{tid}/campaigns/{cid}/approve',json={},headers=hdr).status_code==409
    assert client.post(f'/api/workspaces/{tid}/campaigns/{cid}/submit',json={},headers=hdr).status_code==200
    assert client.post(f'/api/workspaces/{tid}/campaigns/{cid}/approve',json={},headers=hdr).status_code==409
    assert client.post(f'/api/workspaces/{tid}/settings',headers=hdr,
                       json={'mode':'supervised','budget_limit_aed':'100'}).status_code==200
    assert client.post(f'/api/workspaces/{tid}/campaigns/{cid}/approve',json={},headers=hdr).status_code==409
    assert client.post(f'/api/workspaces/{tid}/settings',headers=hdr,
                       json={'mode':'supervised','budget_limit_aed':'200'}).status_code==200
    res=client.post(f'/api/workspaces/{tid}/campaigns/{cid}/approve',json={},headers=hdr)
    assert res.status_code==200 and res.json()['published'] is False
    assert client.post(f'/api/workspaces/{tid}/campaigns/{cid}/approve',json={},headers=hdr).status_code==409
    w=client.get(f'/api/workspaces/{tid}').json()
    assert w['settings']['approved_budget_aed']=='200.00'
    assert w['live_metrics_available'] is False
    assert any(a['action']=='campaign.approved_internal_only' for a in w['audit'])


def test_stop_prevents_approval_and_ai(client):
    tid,hdr=session(client)
    res=client.post(f'/api/workspaces/{tid}/emergency-stop',json={},headers=hdr)
    assert res.status_code==200 and res.json()['external_accounts_paused'] is False
    ai=client.post(f'/api/workspaces/{tid}/agent/plan',headers=hdr,json={
       'brief':'Help promote spa weekend relaxation sessions',
       'service':'Hot stone massage', 'budget_aed':'500','objective':'bookings','provider':'meta'})
    assert ai.status_code==409
    assert client.post(f'/api/workspaces/{tid}/resume-automation',json={},headers=hdr).status_code==200
    ai=client.post(f'/api/workspaces/{tid}/agent/plan',headers=hdr,json={
       'brief':'Help promote spa weekend relaxation sessions',
       'service':'Hot stone massage', 'budget_aed':'500','objective':'bookings','provider':'meta'})
    assert ai.status_code==200
    assert ai.json()['mode'].startswith('Template only')
    assert ai.json()['published'] is False


def test_campaign_research_is_source_grounded_and_draft_only(client, monkeypatch):
    tid, hdr = session(client)
    payload = {'provider': 'meta', 'objective': 'bookings', 'service': 'Swedish massage',
               'budget_aed': '500', 'audience_location': 'Abu Dhabi, UAE',
               'landing_url': 'https://example.com/book', 'brief': 'Weekend appointments'}
    unavailable = client.post(f'/api/workspaces/{tid}/agent/recommend-campaign', headers=hdr, json=payload)
    assert unavailable.status_code == 503

    monkeypatch.setattr(main, 'AI_API_KEY', 'configured')
    monkeypatch.setattr(main, 'AI_BASE_URL', 'https://api.openai.com/v1')
    monkeypatch.setattr(main, 'AI_MODEL', 'test-model')

    async def fake_research(tenant_name, body):
        assert tenant_name and body.provider == 'meta'
        return ({'audience_summary': 'Broad local booking-intent audience',
                 'audience_age_min': 25, 'audience_age_max': 55, 'audience_gender': 'all',
                 'audience_interests': ['massage', 'wellness'],
                 'placements': ['Instagram Feed', 'Instagram Reels'],
                 'call_to_action': 'BOOK_NOW', 'asset_requirements': ['Licensed treatment image'],
                 'creative_angles': ['Quiet weekend reset'], 'missing_inputs': ['Current availability'],
                 'assumptions': ['Service is available in Abu Dhabi'], 'confidence': 'medium',
                 'research_summary': 'Provisional local-service recommendation.'},
                [{'title': 'Meta Advertising Standards',
                  'url': 'https://transparency.meta.com/policies/ad-standards/'}],
                'openai_web_search')

    monkeypatch.setattr(main, 'research_campaign', fake_research)
    response = client.post(f'/api/workspaces/{tid}/agent/recommend-campaign', headers=hdr, json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data['published'] is False
    assert data['recommendation']['confidence'] == 'medium'
    assert data['evidence']['research_mode'] == 'openai_web_search'
    assert data['evidence']['sources'][0]['url'].startswith('https://')
    workspace = client.get(f'/api/workspaces/{tid}').json()
    assert any(item['action'] == 'agent.campaign_researched' for item in workspace['audit'])


def test_meta_and_tiktok_oauth_start_are_scoped(client, monkeypatch):
    tid, hdr = session(client)
    assert client.post(f'/api/workspaces/{tid}/integrations/meta/start', headers=hdr, json={}).status_code == 503
    assert client.post(f'/api/workspaces/{tid}/integrations/tiktok/start', headers=hdr, json={}).status_code == 503
    monkeypatch.setattr(main, 'PUBLIC_ORIGIN', 'https://spa-ads-agent.vercel.app')
    monkeypatch.setattr(main, 'GOOGLE_TOKEN_ENCRYPTION_KEY', Fernet.generate_key().decode())
    monkeypatch.setattr(main, 'META_APP_ID', 'meta-app')
    monkeypatch.setattr(main, 'META_APP_SECRET', 'meta-secret')
    monkeypatch.setattr(main, 'META_LOGIN_CONFIG_ID', '1685284999828927')
    monkeypatch.setattr(main, 'TIKTOK_APP_ID', 'tiktok-app')
    monkeypatch.setattr(main, 'TIKTOK_APP_SECRET', 'tiktok-secret')
    monkeypatch.setattr(main, 'TIKTOK_AUTHORIZATION_URL', 'https://business-api.tiktok.com/authorize?app_id=tiktok-app')
    meta = client.post(f'/api/workspaces/{tid}/integrations/meta/start', headers=hdr, json={})
    tiktok = client.post(f'/api/workspaces/{tid}/integrations/tiktok/start', headers=hdr, json={})
    assert meta.status_code == 200 and 'facebook.com/' in meta.json()['authorization_url']
    assert 'state=' in meta.json()['authorization_url']
    assert 'config_id=1685284999828927' in meta.json()['authorization_url']
    assert 'scope=' not in meta.json()['authorization_url']
    assert tiktok.status_code == 200 and 'business-api.tiktok.com/authorize' in tiktok.json()['authorization_url']
    assert 'state=' in tiktok.json()['authorization_url']


def test_meta_publisher_creates_complete_paused_campaign(client, monkeypatch):
    tid, hdr = session(client)
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(main, 'GOOGLE_TOKEN_ENCRYPTION_KEY', key)
    monkeypatch.setattr(main, 'META_APP_SECRET', 'meta-secret')
    main.save_provider_connection(tid, 'meta', 'meta-access-token', 'act_123', 'Be Relax Meta', 'AED', 'Asia/Dubai')
    created = client.post(f'/api/workspaces/{tid}/campaigns', headers=hdr, json=draft()).json()
    cid = created['id']
    client.post(f'/api/workspaces/{tid}/campaigns/{cid}/submit', headers=hdr, json={})
    client.post(f'/api/workspaces/{tid}/settings', headers=hdr,
                json={'mode': 'supervised', 'budget_limit_aed': '500'})
    assert client.post(f'/api/workspaces/{tid}/campaigns/{cid}/approve', headers=hdr, json={}).status_code == 200

    calls = []
    def fake_meta_post(path, token, payload, message):
        calls.append((path, payload))
        return {'id': str(1000 + len(calls))}
    monkeypatch.setattr(main, 'meta_post', fake_meta_post)
    payload = {'version': 1, 'daily_budget_aed': '25', 'duration_days': 7,
               'page_id': '777', 'instagram_actor_id': '888', 'countries': ['AE'],
               'interest_ids': ['6003139266461'], 'primary_text': 'Book a relaxing massage today.',
               'headline': 'Relax at Be Relax', 'image_url': 'https://example.com/massage.jpg',
               'final_url': 'https://example.com/book', 'call_to_action': 'BOOK_NOW',
               'pixel_id': '999', 'conversion_event': 'SCHEDULE'}
    response = client.post(f'/api/workspaces/{tid}/campaigns/{cid}/publish/meta', headers=hdr, json=payload)
    assert response.status_code == 200
    assert response.json()['status'] == 'PAUSED'
    assert [path.rsplit('/', 1)[-1] for path, _ in calls] == ['campaigns', 'adsets', 'adcreatives', 'ads']
    assert all(call_payload['status'] == 'PAUSED' for _, call_payload in calls if 'status' in call_payload)
    assert client.post(f'/api/workspaces/{tid}/campaigns/{cid}/publish/meta', headers=hdr,
                       json=payload).json()['idempotent'] is True
    assert len(calls) == 4
    workspace = client.get(f'/api/workspaces/{tid}').json()
    assert any(item['action'] == 'campaign.published_meta_paused' for item in workspace['audit'])


def test_minimax_is_primary_provider(client, monkeypatch):
    tid, hdr = session(client)
    monkeypatch.setattr(main, 'MINIMAX_API_KEY', 'configured')
    monkeypatch.setattr(main, 'MINIMAX_BASE_URL', 'https://api.minimax.io/v1')
    monkeypatch.setattr(main, 'MINIMAX_MODEL', 'MiniMax-M3')
    called = []

    async def fake_minimax(tenant_name, body):
        called.append((tenant_name, body.provider))
        return ({'audience_summary': 'Broad local audience', 'audience_age_min': 18,
                 'audience_age_max': 65, 'audience_gender': 'all', 'audience_interests': [],
                 'placements': ['Google Search'], 'call_to_action': 'BOOK_NOW',
                 'asset_requirements': ['Verified service details'], 'creative_angles': ['Convenient booking'],
                 'missing_inputs': [], 'assumptions': [], 'confidence': 'medium',
                 'research_summary': 'Source-grounded draft.'}, [], 'minimax_official_sources')

    monkeypatch.setattr(main, 'research_campaign_minimax', fake_minimax)
    response = client.post(f'/api/workspaces/{tid}/agent/recommend-campaign', headers=hdr, json={
        'provider': 'google', 'objective': 'bookings', 'service': 'Massage', 'budget_aed': '500',
        'audience_location': 'Abu Dhabi, UAE', 'landing_url': '', 'brief': 'Booking campaign'})
    assert response.status_code == 200
    assert called and response.json()['evidence']['ai_provider'] == 'minimax'


def test_malformed_urls_and_precision_rejected(client):
    tid,hdr=session(client)
    body=draft();body['landing_url']='javascript:alert(1)'
    assert client.post(f'/api/workspaces/{tid}/campaigns',headers=hdr,json=body).status_code==422
    body=draft();body['budget_aed']='200.0001'
    assert client.post(f'/api/workspaces/{tid}/campaigns',headers=hdr,json=body).status_code==422
    body=draft();body['budget_aed']='-10'
    assert client.post(f'/api/workspaces/{tid}/campaigns',headers=hdr,json=body).status_code==422


def test_logout_revokes_session(client):
    tid,hdr=session(client)
    assert client.post('/api/logout',headers=hdr,json={}).status_code==200
    assert client.get(f'/api/workspaces/{tid}').status_code==401


def test_google_oauth_connects_and_encrypts_refresh_token(client,monkeypatch):
    tid,hdr=session(client)
    key=Fernet.generate_key().decode()
    monkeypatch.setattr(main,'PUBLIC_ORIGIN','https://spa-ads-agent.vercel.app')
    monkeypatch.setattr(main,'GOOGLE_CLIENT_ID','client-id')
    monkeypatch.setattr(main,'GOOGLE_CLIENT_SECRET','client-secret')
    monkeypatch.setattr(main,'GOOGLE_TOKEN_ENCRYPTION_KEY',key)
    assert client.post(f'/api/workspaces/{tid}/integrations/google/start',json={}).status_code==403
    start=client.post(f'/api/workspaces/{tid}/integrations/google/start',headers=hdr,json={})
    assert start.status_code==200
    query=parse_qs(urlparse(start.json()['authorization_url']).query)
    assert query['scope']==[main.GOOGLE_ADS_SCOPE]
    assert query['prompt']==['select_account consent']
    assert query['redirect_uri']==['https://spa-ads-agent.vercel.app/api/integrations/google/callback']

    class FakeResponse:
        def __init__(self,data,ok=True): self._data,self.is_success=data,ok
        def raise_for_status(self): return None
        def json(self): return self._data

    responses=iter([FakeResponse({'access_token':'access-token','refresh_token':'refresh-token'})])
    monkeypatch.setattr(main.httpx,'post',lambda *args,**kwargs: next(responses))
    callback=client.get('/api/integrations/google/callback',params={'code':'code','state':query['state'][0]},
                        follow_redirects=False)
    assert callback.status_code==303 and 'google=authorized' in callback.headers['location']
    workspace=client.get(f'/api/workspaces/{tid}').json()
    assert workspace['integrations']['google']['status']=='authorized'
    assert workspace['integrations']['google']['customer_id']==''
    with main.connect() as db:
        stored=main.qrow(db,"SELECT refresh_token_encrypted FROM provider_connections WHERE tenant_id=?",(tid,))
    assert 'refresh-token' not in stored['refresh_token_encrypted']
    assert Fernet(key.encode()).decrypt(stored['refresh_token_encrypted'].encode())==b'refresh-token'

    account={'customer_id':'111','login_customer_id':'222','account_name':'Tenant Ads',
             'currency_code':'AED','time_zone':'Asia/Dubai'}
    real_google_access_token=main.google_access_token
    monkeypatch.setattr(main,'google_access_token',lambda connection:'refreshed-access-token')
    monkeypatch.setattr(main,'google_accessible_accounts',lambda token:[account])
    listed=client.get(f'/api/workspaces/{tid}/integrations/google/accounts',headers=hdr)
    assert listed.status_code==200 and listed.json()['accounts']==[account]
    selected=client.post(f'/api/workspaces/{tid}/integrations/google/account',headers=hdr,
                         json={'customer_id':'111','login_customer_id':'222'})
    assert selected.status_code==200
    workspace=client.get(f'/api/workspaces/{tid}').json()
    assert workspace['integrations']['google']['status']=='connected'
    assert workspace['integrations']['google']['customer_id']=='111'
    monkeypatch.setattr(main,'google_access_token',real_google_access_token)

    assert client.post(f'/api/workspaces/{tid}/integrations/google/sync',json={}).status_code==403
    responses=iter([
        FakeResponse({'access_token':'refreshed-access-token'}),
        FakeResponse([{'results':[{'campaign':{'id':'123','name':'Massage Search','status':'ENABLED',
            'advertisingChannelType':'SEARCH'},'segments':{'date':'2026-10-16'},
            'metrics':{'impressions':'1000','clicks':'50',
            'costMicros':'2500000','conversions':3.5}}]}]),
        FakeResponse([{'results':[]}]),
    ])
    sync=client.post(f'/api/workspaces/{tid}/integrations/google/sync',headers=hdr,json={})
    assert sync.status_code==200
    assert sync.json()['totals']=={'impressions':1000,'clicks':50,'cost_aed':'2.50',
                                   'conversions':3.5,'ctr_percent':5.0}
    assert sync.json()['daily'][0]['date']=='2026-10-16'
    workspace=client.get(f'/api/workspaces/{tid}').json()
    assert workspace['live_metrics_available'] is True
    assert workspace['google_metrics']['campaigns'][0]['name']=='Massage Search'

    calls=[]
    conversion_rows=[{'conversionAction':{'id':'11','name':'Spa Ads Agent — Completed Booking',
        'status':'ENABLED','type':'WEBPAGE','category':'BOOK_APPOINTMENT','primaryForGoal':True}},
        {'conversionAction':{'id':'12','name':'Spa Ads Agent — WhatsApp Click','status':'ENABLED',
        'type':'WEBPAGE','category':'MESSAGE_LEAD','primaryForGoal':True}},
        {'conversionAction':{'id':'13','name':'Spa Ads Agent — Phone Call','status':'ENABLED',
        'type':'WEBSITE_CALL','category':'PHONE_CALL_LEAD','primaryForGoal':True}}]
    responses=iter([
        FakeResponse({'access_token':'token'}), FakeResponse([{'results':[]}]),
        FakeResponse({'results':[{'resourceName':'customers/1/conversionActions/11'}]}),
        FakeResponse([{'results':conversion_rows}]),
        FakeResponse({'access_token':'token'}), FakeResponse({'results':[]}),
    ])
    def record_post(*args,**kwargs):
        calls.append((args,kwargs))
        return next(responses)
    monkeypatch.setattr(main.httpx,'post',record_post)
    setup=client.post(f'/api/workspaces/{tid}/integrations/google/conversions/setup',headers=hdr,json={})
    assert setup.status_code==200 and setup.json()['created']==3
    mutate=[x for x in calls if x[0][0].endswith('/conversionActions:mutate')][0]
    assert [op['create']['type'] for op in mutate[1]['json']['operations']]==[
        'WEBPAGE','WEBPAGE','WEBSITE_CALL']
    status=client.post(f'/api/workspaces/{tid}/integrations/google/campaigns/123/status',headers=hdr,
                       json={'status':'PAUSED'})
    assert status.status_code==200 and status.json()['status']=='PAUSED'
    campaign_mutate=[x for x in calls if x[0][0].endswith('/campaigns:mutate')][0]
    assert campaign_mutate[1]['json']['operations'][0]['updateMask']=='status'


def test_ad_account_cannot_be_connected_to_two_workspaces(client, monkeypatch):
    tenant_id,headers=session(client)
    other=client.post('/api/workspaces',headers=headers,json={'name':'Other Business'}).json()['id']
    monkeypatch.setattr(main,'GOOGLE_TOKEN_ENCRYPTION_KEY',Fernet.generate_key().decode())
    main.save_provider_connection(tenant_id,'google','first-token','111','First Business')
    main.save_provider_connection(other,'google','second-token','','Google Ads')
    account={'customer_id':'111','login_customer_id':'222','account_name':'First Business',
             'currency_code':'AED','time_zone':'Asia/Dubai'}
    monkeypatch.setattr(main,'google_access_token',lambda connection:'access-token')
    monkeypatch.setattr(main,'google_accessible_accounts',lambda token:[account])

    response=client.post(f'/api/workspaces/{other}/integrations/google/account',headers=headers,
                         json={'customer_id':'111','login_customer_id':'222'})

    assert response.status_code==409
    assert response.json()['detail']=='This external account is already connected to another workspace'
    with main.connect() as db:
        connection=main.qrow(db,"SELECT customer_id FROM provider_connections "
                                "WHERE tenant_id=? AND provider='google'",(other,))
        bindings=main.qrows(db,"SELECT tenant_id FROM provider_resource_bindings "
                                "WHERE provider='google' AND resource_id='111'")
    assert connection['customer_id']==''
    assert bindings==[{'tenant_id':tenant_id}]


def test_all_external_resource_types_are_exclusive_to_one_workspace(client):
    tenant_id,headers=session(client)
    other=client.post('/api/workspaces',headers=headers,json={'name':'Other Business'}).json()['id']
    resources=[('meta','ad_account'),('tiktok','ad_account'),
               ('google_growth','analytics_property'),
               ('google_growth','search_console_site'),
               ('google_growth','business_account')]
    with main.connect() as db:
        for provider,resource_type in resources:
            resource_id=f'{provider}-{resource_type}'
            main.bind_provider_resource(db,tenant_id,provider,resource_type,resource_id)
            with pytest.raises(main.ProviderResourceConflict):
                main.bind_provider_resource(db,other,provider,resource_type,resource_id)


def test_approved_google_search_campaign_is_created_paused_with_assets_and_audience(client, monkeypatch):
    tid,hdr=session(client)
    body=draft();body.update({'provider':'google','name':'Be Relax Search','service':'Massage Abu Dhabi',
                              'budget_aed':'500.00'})
    cid=client.post(f'/api/workspaces/{tid}/campaigns',headers=hdr,json=body).json()['id']
    client.post(f'/api/workspaces/{tid}/campaigns/{cid}/submit',headers=hdr,json={})
    client.post(f'/api/workspaces/{tid}/settings',headers=hdr,
                json={'mode':'supervised','budget_limit_aed':'500'}).raise_for_status()
    client.post(f'/api/workspaces/{tid}/campaigns/{cid}/approve',headers=hdr,json={}).raise_for_status()
    with main.connect() as db:
        db.execute('''INSERT INTO provider_connections(
                      tenant_id,provider,refresh_token_encrypted,customer_id,login_customer_id,account_name,
                      currency_code,time_zone,status,connected_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                   (tid,'google','encrypted','3021854998','4822753321','Be Relax','AED','Asia/Dubai',
                    'connected',main.utcnow(),main.utcnow()))
    monkeypatch.setattr(main,'google_access_token',lambda connection:'token')
    calls=[]
    def fake_google_post(connection, token, path, payload, error_message, timeout=30):
        calls.append((path,payload))
        if path=='googleAds:searchStream': return []
        if payload.get('validateOnly'): return {}
        return {'mutateOperationResponses':[{}, {'campaignResult': {
            'resourceName':'customers/3021854998/campaigns/987'}}]}
    monkeypatch.setattr(main,'google_post',fake_google_post)
    publish={'version':1,'daily_budget_aed':'70.00','location_ids':['2784'],
             'language_ids':['1000','1019'],'keywords':['massage abu dhabi','massage near me'],
             'headlines':['Be Relax Massage','Massage in Abu Dhabi','Book Your Massage Today'],
             'descriptions':['Professional massage treatments in Abu Dhabi.',
                             'Book your relaxing visit online today.'],
             'callouts':['Easy Online Booking'],'audience_mode':'OBSERVATION',
             'audience_segments':[{'kind':'user_interest','id':'80408'},
                                  {'kind':'user_list','id':'123'}],
             'phone_number':'+971501234567','phone_country_code':'AE',
             'final_url':'https://example.com/book'}
    result=client.post(f'/api/workspaces/{tid}/campaigns/{cid}/publish/google-search',
                       headers=hdr,json=publish)
    assert result.status_code==200 and result.json()['status']=='PAUSED'
    mutate=[payload for path,payload in calls if path=='googleAds:mutate' and not payload['validateOnly']][0]
    operations=mutate['mutateOperations']
    campaign_create=operations[1]['campaignOperation']['create']
    assert campaign_create['status']=='PAUSED'
    assert campaign_create['maximizeConversions']=={}
    assert any('adGroupAdOperation' in operation for operation in operations)
    assert any(operation.get('assetOperation',{}).get('create',{}).get('calloutAsset')
               for operation in operations)
    assert any(operation.get('assetOperation',{}).get('create',{}).get('callAsset')
               for operation in operations)
    ad_group=next(operation['adGroupOperation']['create'] for operation in operations
                  if 'adGroupOperation' in operation)
    assert ad_group['targetingSetting']['targetRestrictions'][0]['bidOnly'] is True
    call_count=len(calls)
    retry=client.post(f'/api/workspaces/{tid}/campaigns/{cid}/publish/google-search',
                      headers=hdr,json=publish)
    assert retry.status_code==200 and retry.json()['idempotent'] is True
    assert len(calls)==call_count
    saved=client.get(f'/api/workspaces/{tid}').json()['campaigns'][0]['publication']
    assert saved['status']=='created' and saved['remote_resource'].endswith('/987')


def test_google_post_parses_stream_error_list(monkeypatch):
    response=main.httpx.Response(
        403,
        request=main.httpx.Request('POST','https://googleads.googleapis.com/v26/test'),
        json=[{'error':{'message':'Developer token is not approved'}}],
    )
    monkeypatch.setattr(main.httpx,'post',lambda *args,**kwargs: response)
    with pytest.raises(main.HTTPException) as exc:
        main.google_post({'customer_id':'123','login_customer_id':'123'},'token',
                         'googleAds:searchStream',{},'Account lookup failed')
    assert exc.value.status_code==502
    assert 'Developer token is not approved' in exc.value.detail


def test_google_publish_requires_approved_budget(client, monkeypatch):
    tid,hdr=session(client)
    body=draft();body['provider']='google'
    cid=client.post(f'/api/workspaces/{tid}/campaigns',headers=hdr,json=body).json()['id']
    payload={'daily_budget_aed':'70','keywords':['massage'],'headlines':['One','Two','Three'],
             'descriptions':['First description','Second description']}
    response=client.post(f'/api/workspaces/{tid}/campaigns/{cid}/publish/google-search',
                         headers=hdr,json=payload)
    assert response.status_code==409 and 'Approve' in response.json()['detail']


def test_meta_and_tiktok_campaign_requirements_are_persisted(client):
    tid,hdr=session(client)
    meta=draft()
    created=client.post(f'/api/workspaces/{tid}/campaigns',headers=hdr,json=meta)
    assert created.status_code==200
    workspace=client.get(f'/api/workspaces/{tid}').json()
    assert workspace['campaigns'][0]['spec']['audience_location']=='Abu Dhabi, UAE'
    assert workspace['campaigns'][0]['spec']['image_urls']==['https://cdn.example.com/massage.jpg']
    tiktok=draft();tiktok.update({'provider':'tiktok','image_urls':'','video_urls':''})
    cid=client.post(f'/api/workspaces/{tid}/campaigns',headers=hdr,json=tiktok).json()['id']
    missing=client.post(f'/api/workspaces/{tid}/campaigns/{cid}/submit',headers=hdr,json={})
    assert missing.status_code==422 and 'video asset' in missing.json()['detail']


def test_google_analytics_supports_all_requested_ranges(client, monkeypatch):
    tid,hdr=session(client)
    connection={'customer_id':'3021854998','login_customer_id':'4822753321','currency_code':'AED',
                'time_zone':'Asia/Dubai'}
    monkeypatch.setattr(main,'google_connection',lambda tenant_id:connection)
    monkeypatch.setattr(main,'google_access_token',lambda value:'token')
    queries=[]
    def fake_post(connection, token, path, payload, error_message, timeout=30):
        queries.append(payload['query'])
        return []
    monkeypatch.setattr(main,'google_post',fake_post)
    monkeypatch.setattr(main,'google_conversion_actions',lambda connection,token:[])
    labels={'yesterday':'Yesterday','this_week':'This week','last_week':'Last week',
            'last_30_days':'Last 30 days'}
    for key,label in labels.items():
        response=client.post(f'/api/workspaces/{tid}/integrations/google/sync?range={key}',headers=hdr,json={})
        assert response.status_code==200 and response.json()['period']==label
        assert 'segments.date BETWEEN' in queries[-1]


def test_google_growth_requests_and_loads_tenant_ga4(client, monkeypatch):
    tid,headers=session(client)
    monkeypatch.setattr(main,'GOOGLE_GROWTH_CLIENT_ID','client-id')
    monkeypatch.setattr(main,'GOOGLE_GROWTH_CLIENT_SECRET','client-secret')
    monkeypatch.setattr(main,'GOOGLE_TOKEN_ENCRYPTION_KEY',Fernet.generate_key().decode())
    monkeypatch.setattr(main,'PUBLIC_ORIGIN','https://ads-wise.com')
    start=client.post(f'/api/workspaces/{tid}/integrations/google-growth/start',headers=headers,json={})
    scopes=parse_qs(urlparse(start.json()['authorization_url']).query)['scope'][0]
    assert 'analytics.readonly' in scopes

    class Response:
        def __init__(self,payload): self.payload=payload
        def raise_for_status(self): return None
        def json(self): return self.payload

    def fake_get(url,**kwargs):
        if 'mybusinessaccountmanagement' in url: return Response({'accounts':[]})
        if 'searchconsole' in url: return Response({'siteEntry':[]})
        return Response({'accountSummaries':[{'displayName':'Tenant account','propertySummaries':[
            {'property':'properties/123','displayName':'Tenant website'}]}]})

    reports=[]
    def fake_post(url,**kwargs):
        reports.append(kwargs['json'])
        if 'dimensions' not in kwargs['json']:
            return Response({'rows':[{'metricValues':[{'value':'120'},{'value':'45'},
                                                       {'value':'180'},{'value':'900'}]}]})
        return Response({'rows':[{'dimensionValues':[{'value':'/book'}],
                                  'metricValues':[{'value':'80'},{'value':'60'}]}]})

    monkeypatch.setattr(main.httpx,'get',fake_get)
    monkeypatch.setattr(main.httpx,'post',fake_post)
    snapshot=main.google_growth_data('token',analytics_property='properties/123')
    assert snapshot['google_analytics']['property']=='properties/123'
    assert snapshot['google_analytics']['totals']['sessions']==180
    assert snapshot['google_analytics']['top_pages'][0]['page']=='/book'
    assert len(reports)==2


def test_google_growth_keeps_selected_search_console_property(monkeypatch):
    class Response:
        def __init__(self,payload): self.payload=payload
        def raise_for_status(self): return None
        def json(self): return self.payload

    def fake_get(url,**kwargs):
        if 'mybusinessaccountmanagement' in url: return Response({'accounts':[]})
        if 'searchconsole' in url:
            return Response({'siteEntry':[{'siteUrl':'https://first.example/'},
                                          {'siteUrl':'https://tenant.example/'}]})
        return Response({'accountSummaries':[]})

    requests=[]
    def fake_post(url,**kwargs):
        assert 'https%3A%2F%2Ftenant.example%2F' in url
        requests.append(kwargs['json'])
        dimensions=kwargs['json'].get('dimensions')
        if not dimensions:
            return Response({'rows':[{'clicks':12,'impressions':240,'ctr':.05,'position':7.25}]})
        name='tenant search' if dimensions==['query'] else 'https://tenant.example/page'
        return Response({'rows':[{'keys':[name],'clicks':7,'impressions':90}]})

    monkeypatch.setattr(main.httpx,'get',fake_get)
    monkeypatch.setattr(main.httpx,'post',fake_post)
    snapshot=main.google_growth_data('token',search_console_site='https://tenant.example/')
    assert snapshot['search_console']['site_url']=='https://tenant.example/'
    assert snapshot['search_console']['totals']=={
        'clicks':12.0,'impressions':240.0,'ctr_percent':5.0,'position':7.25}
    assert snapshot['search_console']['top_queries'][0]['name']=='tenant search'
    assert snapshot['search_console']['top_pages'][0]['name']=='https://tenant.example/page'
    assert [request.get('dimensions') for request in requests]==[None,['query'],['page']]


def test_google_growth_does_not_default_to_another_profile(monkeypatch):
    class Response:
        def __init__(self, payload): self.payload = payload
        def raise_for_status(self): return None
        def json(self): return self.payload

    def fake_get(url, **kwargs):
        if 'mybusinessaccountmanagement' in url:
            return Response({'accounts': [{'name': 'accounts/1', 'accountName': 'Another business'}]})
        if 'searchconsole' in url:
            return Response({'siteEntry': [{'siteUrl': 'https://another.example/'}]})
        return Response({'accountSummaries': [{'propertySummaries': [
            {'property': 'properties/999', 'displayName': 'Another website'}]}]})

    monkeypatch.setattr(main.httpx, 'get', fake_get)
    monkeypatch.setattr(main.httpx, 'post', lambda *args, **kwargs: pytest.fail('No profile report should run'))
    snapshot = main.google_growth_data('token')
    assert snapshot['locations'] == []
    assert snapshot['search_console'] is None
    assert snapshot['google_analytics'] is None


def test_workspace_growth_snapshot_exposes_only_assigned_profiles():
    snapshot = {
        'business_accounts': [{'name': 'accounts/1'}, {'name': 'accounts/2'}],
        'locations': [{'name': 'locations/1'}],
        'search_console_sites': [{'siteUrl': 'https://one.example/'},
                                 {'siteUrl': 'https://two.example/'}],
        'search_console': {'site_url': 'https://two.example/'},
        'analytics_properties': [{'property': 'properties/1'}, {'property': 'properties/2'}],
        'google_analytics': {'property': 'properties/2'}
    }
    public = main.workspace_growth_snapshot(snapshot, {'customer_id': 'accounts/2'})
    assert public['business_accounts'] == [{'name': 'accounts/2'}]
    assert public['search_console_sites'] == [{'siteUrl': 'https://two.example/'}]
    assert public['analytics_properties'] == [{'property': 'properties/2'}]
    assert len(snapshot['business_accounts']) == 2
