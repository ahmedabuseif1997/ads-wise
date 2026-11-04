"""Google Search and YouTube (Demand Gen) launches: Seed validation, owner approval, ACTIVE, isolation.

Every Google Ads call is served by FakeGoogle; no test reaches Google, YouTube or BytePlus.
"""
import os
import re
import secrets

os.environ.setdefault('ADMIN_EMAIL', 'owner@example.com')
os.environ.setdefault('ADMIN_PASSWORD', 'really-long-integration-password-123')
os.environ.setdefault('COOKIE_SECURE', 'false')

import httpx
import pytest
from fastapi.testclient import TestClient
from app import main

ACCOUNT = '3021854998'
VIDEO = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'DB_PATH', tmp_path / 'adsagent.db')
    for name in ('AI_API_KEY', 'MINIMAX_API_KEY', 'META_APP_ID', 'META_APP_SECRET', 'META_LOGIN_CONFIG_ID',
                 'TIKTOK_APP_ID', 'TIKTOK_APP_SECRET', 'TIKTOK_AUTHORIZATION_URL', 'RESEND_API_KEY'):
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


class FakeGoogle:
    """In-memory Google Ads API. Each call must use the requesting workspace's own account."""

    def __init__(self):
        self.calls = []
        self.accounts = {ACCOUNT: {'id': ACCOUNT, 'currencyCode': 'AED', 'status': 'ENABLED'},
                         '4000000001': {'id': '4000000001', 'currencyCode': 'AED', 'status': 'ENABLED'}}
        self.remote = {'5001': {'customer': ACCOUNT, 'id': '5001', 'name': 'Existing search',
                                'advertisingChannelType': 'SEARCH', 'status': 'ENABLED',
                                'campaignBudget': f'customers/{ACCOUNT}/campaignBudgets/7001'},
                       '5002': {'customer': ACCOUNT, 'id': '5002', 'name': 'Classic YouTube video',
                                'advertisingChannelType': 'VIDEO', 'status': 'ENABLED',
                                'campaignBudget': f'customers/{ACCOUNT}/campaignBudgets/7002'},
                       '6001': {'customer': '4000000001', 'id': '6001', 'name': 'Other business',
                                'advertisingChannelType': 'SEARCH', 'status': 'ENABLED',
                                'campaignBudget': 'customers/4000000001/campaignBudgets/7003'}}
        self.next_id = 987
        self.seed_reviews = []
        self.private_videos = set()
        self.logo_error = ''

    def mutations(self):
        return [call for call in self.calls if call[1] != 'googleAds:searchStream']

    def __call__(self, connection, token, path, payload, error_message, timeout=30):
        customer = connection['customer_id']
        self.calls.append((customer, path, payload))
        if path == 'googleAds:searchStream':
            query = payload['query']
            if 'FROM customer' in query:
                return [{'results': [{'customer': self.accounts[customer]}]}]
            by_id = re.search(r'campaign\.id = (\d+)', query)
            if by_id:
                item = self.remote.get(by_id.group(1))
                return [{'results': [{'campaign': {k: v for k, v in item.items() if k != 'customer'}}]}] \
                    if item and item['customer'] == customer else []
            by_name = re.search(r"campaign\.name = '(.+?)'", query)
            if by_name:
                found = next((cid for cid, item in self.remote.items()
                              if item['customer'] == customer and item['name'] == by_name.group(1)), None)
                return [{'results': [{'campaign': {'resourceName': f'customers/{customer}/campaigns/{found}'}}]}] \
                    if found else []
            return []
        if path == 'googleAds:mutate':
            if payload['validateOnly']:
                return {}
            create = payload['mutateOperations'][1]['campaignOperation']['create']
            campaign_id = str(self.next_id)
            self.next_id += 1
            self.remote[campaign_id] = {'customer': customer, 'id': campaign_id, 'name': create['name'],
                                        'advertisingChannelType': create['advertisingChannelType'],
                                        'status': create['status'],
                                        'campaignBudget': f'customers/{customer}/campaignBudgets/{campaign_id}0'}
            return {'mutateOperationResponses': [{'campaignBudgetResult': {}}, {'campaignResult': {
                'resourceName': f'customers/{customer}/campaigns/{campaign_id}'}}]}
        if path == 'campaigns:mutate':
            for operation in payload['operations']:
                self.remote[operation['update']['resourceName'].rsplit('/', 1)[-1]]['status'] = \
                    operation['update']['status']
            return {}
        if path == 'campaignBudgets:mutate':
            return {}
        raise AssertionError(f'Unexpected Google Ads call {path}')


@pytest.fixture
def google(monkeypatch):
    fake = FakeGoogle()
    monkeypatch.setattr(main, 'google_post', fake)
    monkeypatch.setattr(main, 'google_access_token', lambda connection: 'google-token')
    monkeypatch.setattr(main, 'GOOGLE_ADS_DEVELOPER_TOKEN', 'dev-token')
    monkeypatch.setattr(main, 'ARK_API_KEY', 'ark-test-key')
    monkeypatch.setattr(main, 'ARK_BASE_URL', 'https://ark.ap-southeast.bytepluses.com/api/v3')
    monkeypatch.setattr(main, 'ARK_MODEL', 'seed-2-0-pro-260328')

    def seed_review(review):
        fake.seed_reviews.append(review)
        return {'decision': 'pass', 'summary': 'Clear, compliant spa offer.', 'issues': []}

    def video_details(video_id):
        return None if video_id in fake.private_videos else {'title': '60-minute massage tour', 'channel': 'Be Relax'}

    def logo(url):
        if fake.logo_error:
            raise main.HTTPException(422, fake.logo_error)
        return {'data': 'bG9nbw==', 'mime_type': 'image/png'}

    monkeypatch.setattr(main, 'seed_review_meta_change', seed_review)
    monkeypatch.setattr(main, 'youtube_video_details', video_details)
    monkeypatch.setattr(main, 'fetch_logo_image', logo)
    return fake


def connect_google(tid, customer=ACCOUNT):
    with main.connect() as db:
        db.execute('''INSERT INTO provider_connections(tenant_id,provider,refresh_token_encrypted,customer_id,
                      login_customer_id,account_name,currency_code,time_zone,status,connected_at,updated_at)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                   (tid, 'google', 'encrypted', customer, '', 'Be Relax', 'AED', 'Asia/Dubai', 'connected',
                    main.utcnow(), main.utcnow()))
        main.bind_provider_resource(db, tid, 'google', 'ad_account', customer)


def ready(client, customer=ACCOUNT):
    tid, hdr = session(client)
    connect_google(tid, customer)
    client.post(f'/api/workspaces/{tid}/settings', headers=hdr,
                json={'mode': 'supervised', 'budget_limit_aed': '500'}).raise_for_status()
    return tid, hdr


def campaign(client, tid, hdr, provider):
    body = {'name': 'Weekend massage', 'provider': provider, 'objective': 'bookings', 'service': 'Swedish massage',
            'brief': 'Promote weekend sessions', 'copy': 'Unwind this weekend.', 'landing_url': 'https://example.com/book',
            'budget_aed': '200.00', 'audience_location': 'Abu Dhabi, UAE', 'audience_age_min': 25,
            'audience_age_max': 55, 'audience_gender': 'all', 'audience_interests': 'massage',
            'placements': 'YouTube', 'video_urls': VIDEO if provider == 'youtube' else '', 'call_to_action': 'BOOK_NOW'}
    cid = client.post(f'/api/workspaces/{tid}/campaigns', headers=hdr, json=body).json()['id']
    submitted = client.post(f'/api/workspaces/{tid}/campaigns/{cid}/submit', headers=hdr, json={})
    assert submitted.status_code == 200, submitted.text
    return cid


def search_launch(daily='25'):
    return {'daily_budget_aed': daily, 'duration_days': 7, 'keywords': ['massage abu dhabi'],
            'headlines': ['Be Relax Massage', 'Massage in Abu Dhabi', 'Book Your Massage Today'],
            'descriptions': ['Professional massage treatments in Abu Dhabi.', 'Book your relaxing visit online today.'],
            'final_url': 'https://example.com/book'}


def youtube_launch(daily='20', **overrides):
    return {'daily_budget_aed': daily, 'duration_days': 7, 'youtube_video_url': VIDEO,
            'headlines': ['Unwind this weekend'], 'long_headline': 'Book a 60-minute Swedish massage in Abu Dhabi',
            'descriptions': ['Licensed therapists. Easy online booking.'], 'business_name': 'Be Relax Spa',
            'logo_image_url': 'https://cdn.example.com/logo.png', 'final_url': 'https://example.com/book', **overrides}


def request(client, tid, hdr, body):
    response = client.post(f'/api/workspaces/{tid}/integrations/google/change-requests', headers=hdr, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def approve(client, tid, hdr, request_id):
    return client.post(f'/api/workspaces/{tid}/integrations/google/change-requests/{request_id}/approve',
                       headers=hdr, json={})


def failed(item):
    return {check['key'] for check in item['seed_report']['checks'] if not check['passed']}


def member(tid, email, role):
    with main.connect() as db:
        uid = secrets.token_hex(12)
        db.execute('INSERT INTO users VALUES(?,?,?,?)',
                   (uid, email, main.hash_password('member-password-long-123'), main.utcnow()))
        db.execute('INSERT INTO memberships VALUES(?,?,?)', (uid, tid, role))
    other = TestClient(main.app)
    assert other.post('/api/login', json={'email': email, 'password': 'member-password-long-123'}).status_code == 200
    return other, {'X-CSRF-Token': other.get('/api/bootstrap').json()['csrf']}


def test_youtube_links_are_parsed_to_video_ids():
    for url in (VIDEO, 'https://youtu.be/dQw4w9WgXcQ', 'https://www.youtube.com/shorts/dQw4w9WgXcQ',
                'https://m.youtube.com/watch?v=dQw4w9WgXcQ&t=10', 'dQw4w9WgXcQ'):
        assert main.youtube_video_id(url) == 'dQw4w9WgXcQ'
    for url in ('https://example.com/watch?v=dQw4w9WgXcQ', 'https://youtu.be/short', '', 'not a link'):
        assert main.youtube_video_id(url) == ''


def test_youtube_campaigns_need_a_youtube_link_to_submit(client):
    tid, hdr = session(client)
    body = {'name': 'Weekend massage', 'provider': 'youtube', 'objective': 'bookings', 'service': 'Massage',
            'brief': 'b', 'copy': 'Unwind.', 'landing_url': 'https://example.com/book', 'budget_aed': '200.00',
            'audience_location': 'Abu Dhabi, UAE', 'video_urls': 'https://cdn.example.com/clip.mp4'}
    cid = client.post(f'/api/workspaces/{tid}/campaigns', headers=hdr, json=body).json()['id']
    response = client.post(f'/api/workspaces/{tid}/campaigns/{cid}/submit', headers=hdr, json={})
    assert response.status_code == 422 and 'YouTube' in response.json()['detail']


def test_search_launch_needs_seed_then_owner_and_goes_live_enabled(client, google):
    tid, hdr = ready(client)
    cid = campaign(client, tid, hdr, 'google')
    manager, manager_hdr = member(tid, 'manager@example.com', 'manager')
    item = request(manager, tid, manager_hdr, {'action': 'publish_search', 'campaign_id': cid, 'search': search_launch()})
    assert item['status'] == 'awaiting_owner' and failed(item) == set()
    assert {'developer_token', 'account_live', 'asset_ownership', 'seed_ai_review'} <= {
        check['key'] for check in item['seed_report']['checks']}
    assert google.mutations() == []  # nothing reaches Google before the owner approves
    assert approve(manager, tid, manager_hdr, item['id']).status_code == 403
    done = approve(client, tid, hdr, item['id'])
    assert done.status_code == 200, done.text
    assert done.json()['status'] == 'executed' and done.json()['result']['status'] == 'ENABLED'
    mutate = [call[2] for call in google.calls if call[1] == 'googleAds:mutate']
    assert [payload['validateOnly'] for payload in mutate] == [True, False]  # dry run first
    assert mutate[1]['mutateOperations'][1]['campaignOperation']['create']['status'] == 'ENABLED'
    workspace = client.get(f'/api/workspaces/{tid}').json()
    launched = next(item for item in workspace['campaigns'] if item['id'] == cid)
    assert launched['status'] == 'approved' and launched['publication']['status'] == 'active'
    actions = {entry['action'] for entry in workspace['audit']}
    assert {'google.change_requested', 'google.change_executed_live', 'campaign.published_google_active'} <= actions
    assert approve(client, tid, hdr, item['id']).status_code == 409


def test_youtube_launch_is_a_youtube_only_demand_gen_campaign_created_enabled(client, google):
    tid, hdr = ready(client)
    cid = campaign(client, tid, hdr, 'youtube')
    item = request(client, tid, hdr, {'action': 'publish_youtube', 'campaign_id': cid,
                                      'youtube': youtube_launch(target_cpa_aed='30')})
    assert item['status'] == 'awaiting_owner', item['seed_report']
    assert {'youtube_video_live', 'logo_image'} <= {check['key'] for check in item['seed_report']['checks']}
    review = google.seed_reviews[-1]
    assert review['platform'] == 'youtube' and review['creative']['youtube_video_title'] == '60-minute massage tour'
    done = approve(client, tid, hdr, item['id'])
    assert done.status_code == 200, done.text
    assert done.json()['result']['channel'] == 'DEMAND_GEN (YouTube)'
    operations = [call[2] for call in google.calls if call[1] == 'googleAds:mutate'][-1]['mutateOperations']
    budget = operations[0]['campaignBudgetOperation']['create']
    assert budget['explicitlyShared'] is False and budget['amountMicros'] == '20000000'
    created = operations[1]['campaignOperation']['create']
    assert (created['advertisingChannelType'], created['status']) == ('DEMAND_GEN', 'ENABLED')
    assert created['targetCpa'] == {'targetCpaMicros': '30000000'} and 'advertisingChannelSubType' not in created
    ad_group = operations[2]['adGroupOperation']['create']
    assert 'type' not in ad_group
    assert ad_group['demandGenAdGroupSettings']['channelControls']['selectedChannels'] == {
        'gmail': False, 'discover': False, 'display': False,
        'youtubeInFeed': True, 'youtubeInStream': True, 'youtubeShorts': True}
    criteria = [op['adGroupCriterionOperation']['create'] for op in operations if 'adGroupCriterionOperation' in op]
    assert criteria[0]['location'] == {'geoTargetConstant': 'geoTargetConstants/2784'}  # ad group level
    assert [item['language']['languageConstant'] for item in criteria if 'language' in item] == [
        'languageConstants/1000', 'languageConstants/1019']
    assets = [op['assetOperation']['create'] for op in operations if 'assetOperation' in op]
    assert assets[0]['youtubeVideoAsset'] == {'youtubeVideoId': 'dQw4w9WgXcQ'}
    assert assets[1]['type'] == 'IMAGE' and assets[1]['imageAsset'] == {'data': 'bG9nbw=='}
    ad = operations[-1]['adGroupAdOperation']['create']
    assert ad['status'] == 'ENABLED' and ad['ad']['finalUrls'] == ['https://example.com/book']
    video_ad = ad['ad']['demandGenVideoResponsiveAd']
    assert video_ad['businessName'] == {'text': 'Be Relax Spa'}
    assert video_ad['videos'] == [{'asset': assets[0]['resourceName']}]
    assert video_ad['logoImages'] == [{'asset': assets[1]['resourceName']}]
    assert video_ad['longHeadlines'] == [{'text': 'Book a 60-minute Swedish massage in Abu Dhabi'}]


def test_seed_blocks_unsafe_google_and_youtube_requests_before_the_owner(client, google, monkeypatch):
    tid, hdr = ready(client)
    youtube_id = campaign(client, tid, hdr, 'youtube')
    over = request(client, tid, hdr, {'action': 'publish_youtube', 'campaign_id': youtube_id,
                                      'youtube': youtube_launch(daily='40')})
    assert 'budget_upper_bounds' in failed(over)
    google.private_videos.add('dQw4w9WgXcQ')
    private = request(client, tid, hdr, {'action': 'publish_youtube', 'campaign_id': youtube_id, 'youtube': youtube_launch()})
    assert 'youtube_video_live' in failed(private)
    google.private_videos.clear()
    google.logo_error = 'The logo URL must return a PNG, JPEG or GIF image'
    logo = request(client, tid, hdr, {'action': 'publish_youtube', 'campaign_id': youtube_id, 'youtube': youtube_launch()})
    assert 'logo_image' in failed(logo)
    google.logo_error = ''
    google.accounts[ACCOUNT]['currencyCode'] = 'USD'
    usd = request(client, tid, hdr, {'action': 'publish_youtube', 'campaign_id': youtube_id, 'youtube': youtube_launch()})
    assert 'account_live' in failed(usd)
    google.accounts[ACCOUNT]['currencyCode'] = 'AED'
    search_id = campaign(client, tid, hdr, 'google')
    wrong_kind = request(client, tid, hdr, {'action': 'publish_youtube', 'campaign_id': search_id,
                                            'youtube': youtube_launch()})
    assert 'campaign' in failed(wrong_kind)
    monkeypatch.setattr(main, 'GOOGLE_ADS_DEVELOPER_TOKEN', '')
    no_token = request(client, tid, hdr, {'action': 'publish_search', 'campaign_id': search_id, 'search': search_launch()})
    assert {'developer_token', 'token_valid', 'seed_ai_review'} <= failed(no_token)
    monkeypatch.setattr(main, 'GOOGLE_ADS_DEVELOPER_TOKEN', 'dev-token')
    monkeypatch.setattr(main, 'ARK_API_KEY', '')
    no_seed = request(client, tid, hdr, {'action': 'publish_search', 'campaign_id': search_id, 'search': search_launch()})
    assert failed(no_seed) == {'seed_ai_review'}  # Seed AI is obligatory and fails closed
    assert google.mutations() == []


def test_status_and_budget_changes_are_owner_approved_and_limited_to_this_account(client, google):
    tid, hdr = ready(client)
    cid = campaign(client, tid, hdr, 'google')
    launch = request(client, tid, hdr, {'action': 'publish_search', 'campaign_id': cid, 'search': search_launch()})
    live_id = approve(client, tid, hdr, launch['id']).json()['result']['campaign_id']
    enable_external = request(client, tid, hdr, {'action': 'set_status', 'target_id': '5001', 'status': 'ENABLED'})
    assert 'managed_campaign' in failed(enable_external)
    pause_external = request(client, tid, hdr, {'action': 'set_status', 'target_id': '5001', 'status': 'PAUSED'})
    assert pause_external['status'] == 'awaiting_owner'
    pause_video = request(client, tid, hdr, {'action': 'set_status', 'target_id': '5002', 'status': 'PAUSED'})
    assert 'target_mutable' in failed(pause_video)  # Google forbids API changes to classic Video campaigns
    other_account = request(client, tid, hdr, {'action': 'set_status', 'target_id': '6001', 'status': 'PAUSED'})
    assert 'target_in_account' in failed(other_account)
    too_high = request(client, tid, hdr, {'action': 'set_budget', 'target_id': live_id, 'daily_budget_aed': '30'})
    assert 'budget_upper_bounds' in failed(too_high)
    budget = request(client, tid, hdr, {'action': 'set_budget', 'target_id': live_id, 'daily_budget_aed': '20'})
    assert budget['status'] == 'awaiting_owner'
    assert approve(client, tid, hdr, budget['id']).status_code == 200
    update = [call[2] for call in google.calls if call[1] == 'campaignBudgets:mutate'][-1]['operations'][0]
    assert update['update']['amountMicros'] == '20000000' and update['updateMask'] == 'amountMicros'
    legacy = client.post(f'/api/workspaces/{tid}/integrations/google/campaigns/5001/status', headers=hdr,
                         json={'status': 'PAUSED'})
    assert legacy.status_code == 200 and legacy.json()['status'] == 'awaiting_owner'
    assert google.remote['5001']['status'] == 'ENABLED'  # nothing changed until the owner approves


def test_emergency_stop_pauses_only_campaigns_adswise_launched(client, google):
    tid, hdr = ready(client)
    cid = campaign(client, tid, hdr, 'youtube')
    item = request(client, tid, hdr, {'action': 'publish_youtube', 'campaign_id': cid, 'youtube': youtube_launch()})
    live_id = approve(client, tid, hdr, item['id']).json()['result']['campaign_id']
    stop = client.post(f'/api/workspaces/{tid}/emergency-stop', headers=hdr, json={}).json()
    assert stop['external_accounts_paused'] is True and stop['google'] == {'paused': 1, 'failed': 0}
    assert google.remote[live_id]['status'] == 'PAUSED'
    assert google.remote['5001']['status'] == 'ENABLED'  # campaigns created outside Adswise are left alone
    blocked = request(client, tid, hdr, {'action': 'set_status', 'target_id': live_id, 'status': 'ENABLED'})
    assert 'workspace_controls' in failed(blocked)


def test_google_requests_never_cross_workspaces(client, google):
    tid, hdr = ready(client)
    cid = campaign(client, tid, hdr, 'google')
    item = request(client, tid, hdr, {'action': 'publish_search', 'campaign_id': cid, 'search': search_launch()})
    other = client.post('/api/workspaces', headers=hdr, json={'name': 'Other Business'}).json()['id']
    connect_google(other, '4000000001')
    assert approve(client, other, hdr, item['id']).status_code == 404
    assert client.get(f'/api/workspaces/{other}/integrations/google/change-requests').json()['requests'] == []
    before = len(google.calls)
    stolen = request(client, other, hdr, {'action': 'publish_search', 'campaign_id': cid, 'search': search_launch()})
    assert 'campaign' in failed(stolen)
    assert google.calls[before:] and all(call[0] == '4000000001' for call in google.calls[before:])
    with main.connect() as db:
        db.execute("DELETE FROM provider_resource_bindings WHERE tenant_id=? AND provider='google'", (other,))
        main.bind_provider_resource(db, tid, 'google', 'ad_account', 'shared-check')
    unbound = request(client, other, hdr, {'action': 'set_status', 'target_id': '6001', 'status': 'PAUSED'})
    assert 'asset_ownership' in failed(unbound)
    assert google.mutations() == []


def test_logo_download_rejects_private_hosts_and_non_images(monkeypatch):
    monkeypatch.setattr(main, 'safe_public_url', lambda url: False)
    with pytest.raises(main.HTTPException) as private:
        main.fetch_logo_image('https://169.254.169.254/logo.png')
    assert private.value.status_code == 422
    monkeypatch.setattr(main, 'safe_public_url', lambda url: True)
    monkeypatch.setattr(main.httpx, 'get', lambda url, **kwargs: httpx.Response(
        200, headers={'content-type': 'text/html'}, content=b'<html>', request=httpx.Request('GET', url)))
    with pytest.raises(main.HTTPException) as html:
        main.fetch_logo_image('https://cdn.example.com/logo.png')
    assert 'PNG, JPEG or GIF' in html.value.detail
    monkeypatch.setattr(main.httpx, 'get', lambda url, **kwargs: httpx.Response(
        200, headers={'content-type': 'image/png'}, content=b'\x89PNG', request=httpx.Request('GET', url)))
    assert main.fetch_logo_image('https://cdn.example.com/logo.png') == {'data': 'iVBORw==', 'mime_type': 'image/png'}
