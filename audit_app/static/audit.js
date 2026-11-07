'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let session = null, report = null, signupMode = false;
function message(text, error = false) {
  $('message').textContent = text;
  $('message').classList.toggle('hidden', !text);
  $('message').classList.toggle('error', error);
}
async function api(path, data) {
  const options = {credentials:'same-origin', headers:{}};
  if (data !== undefined) {
    options.method = 'POST';
    options.headers['Content-Type'] = 'application/json';
    if (session) options.headers['X-CSRF-Token'] = session.csrf;
    options.body = JSON.stringify(data);
  }
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok) {
    if (response.status === 401 && session) {
      session = null;
      $('workspace').classList.add('hidden'); $('logout').classList.add('hidden'); $('auth').classList.remove('hidden');
      $('report').replaceChildren(); report = null;
    }
    throw new Error(typeof result.detail === 'string' ? result.detail : 'Check the form fields and try again.');
  }
  return result;
}
async function busy(button, action) {
  button.disabled = true; const label = button.textContent; button.textContent = 'Please wait…'; message('');
  try { await action(); } catch (error) { message(error.message, true); }
  finally { button.disabled = false; button.textContent = label; }
}
function authMode(signup) {
  signupMode = signup;
  document.querySelectorAll('.signup-only').forEach(x => x.classList.toggle('hidden', !signup));
  $('business').required = signup; $('invitation').required = false;
  $('loginTab').classList.toggle('active', !signup); $('signupTab').classList.toggle('active', signup);
  $('loginTab').setAttribute('aria-pressed', String(!signup)); $('signupTab').setAttribute('aria-pressed', String(signup));
  $('password').autocomplete = signup ? 'new-password' : 'current-password';
  $('authTitle').textContent = signup ? 'Create a separate audit account' : 'Welcome to your audit workspace';
  $('authSubmit').textContent = signup ? 'Request access →' : 'Sign in →';
}
$('loginTab').addEventListener('click', () => authMode(false));
$('signupTab').addEventListener('click', () => authMode(true));
$('authForm').addEventListener('submit', event => {
  event.preventDefault();
  busy($('authSubmit'), async () => {
    const body = {email:$('email').value, password:$('password').value};
    if (signupMode) Object.assign(body, {business:$('business').value, invitation_code:$('invitation').value});
    const result = await api(signupMode ? '/api/signup' : '/api/login', body);
    if (result.pending_approval) { $('password').value = ''; authMode(false); message('Request submitted. Your administrator must approve access before you can sign in.'); return; }
    $('password').value = ''; $('invitation').value = ''; await boot();
  });
});
async function boot() {
  try { session = await api('/api/me'); }
  catch (error) {
    $('auth').classList.remove('hidden'); $('workspace').classList.add('hidden'); $('logout').classList.add('hidden');
    if (error.message !== 'Sign in to your audit account') message(error.message, true);
    return;
  }
  $('auth').classList.add('hidden'); $('workspace').classList.remove('hidden'); $('logout').classList.remove('hidden');
  $('tenantName').textContent = session.name; $('userEmail').textContent = session.email;
  $('adminPanel').classList.toggle('hidden', !session.is_admin);
  if (session.is_admin) await loadRequests();
  const c = session.connection;
  $('accountForm').classList.toggle('hidden', !c); $('disconnect').classList.toggle('hidden', !c);
  $('customer').value = c?.customer_id || ''; $('manager').value = c?.manager_id || '';
  $('connectionStatus').textContent = c?.customer_id ? `Connected: ${c.account_name} · ${c.customer_id}` : c ? 'Google authorized. Verify an advertising account below.' : session.google_configured ? 'No Google account connected.' : 'Google connection setup is pending for this deployment.';
  $('run').disabled = !c?.customer_id;
  report = await api('/api/reports/latest'); renderReport();
  const google = new URLSearchParams(location.search).get('google');
  if (google) { message(google === 'connected' ? 'Google authorized. Enter your Google Ads customer ID to verify your account.' : 'Google authorization was cancelled.'); history.replaceState(null, '', '/'); }
}
$('logout').addEventListener('click', () => busy($('logout'), async () => { await api('/api/logout', {}); session = null; report = null; renderReport(); await boot(); }));
$('connect').addEventListener('click', () => busy($('connect'), async () => { const result = await api('/api/google/start', {}); location.assign(result.url); }));
$('accountForm').addEventListener('submit', event => {
  event.preventDefault();
  busy(event.submitter, async () => {
    await api('/api/google/select', {customer_id:$('customer').value.replace(/[- ]/g,''), manager_id:$('manager').value.replace(/[- ]/g,'')});
    await boot(); message('Account access verified. You can now run your health check.');
  });
});
$('disconnect').addEventListener('click', () => {
  if (!confirm('Disconnect this workspace’s Google connection and delete its saved audit reports? This does not change your Google Ads account.')) return;
  busy($('disconnect'), async () => { await api('/api/google/disconnect', {}); await boot(); message('Disconnected. Saved audit reports were deleted. You can also revoke consent in your Google account.'); });
});
$('auditForm').addEventListener('submit', event => {
  event.preventDefault();
  busy($('run'), async () => { report = await api('/api/reports', {goal:$('goal').value, offers_home_visits:$('homeVisits').checked}); renderReport(); message('Health check complete. Expand a finding to review the evidence and instructions.'); });
});
function amount(value) {
  try { return new Intl.NumberFormat(undefined, {style:'currency', currency:report.currency, maximumFractionDigits:2}).format(value); }
  catch { return `${Number(value).toFixed(2)} ${report.currency || 'account currency'}`; }
}
function renderReport() {
  $('empty').classList.toggle('hidden', !!report); $('report').classList.toggle('hidden', !report);
  if (!report) { $('report').replaceChildren(); return; }
  $('goal').value = report.options.goal; $('homeVisits').checked = report.options.offers_home_visits;
  const cost = report.campaigns.reduce((sum,c) => sum + c.cost_micros / 1000000, 0);
  const conversions = report.campaigns.reduce((sum,c) => sum + c.conversions, 0);
  const done = new Set(report.completed);
  $('report').innerHTML = `<div class="report-head"><div><p class="eyebrow">YOUR ACTION PLAN</p><h2>${esc(report.account_name)}</h2><div class="small">${esc(report.start)} – ${esc(report.end)} · Account time zone</div></div><span class="pill">${report.findings.length} findings</span></div><div class="stats"><div class="stat"><span class="small">Spend</span><strong>${esc(amount(cost))}</strong></div><div class="stat"><span class="small">Reported conversions</span><strong>${esc(Number(conversions.toFixed(2)))}</strong></div><div class="stat"><span class="small">Cost / conversion</span><strong>${conversions ? esc(amount(cost/conversions)) : '—'}</strong></div></div><p class="small">Conversions may include enquiries or other actions. They are not necessarily confirmed bookings.</p><p class="small">${done.size} of ${report.findings.length} marked fixed · Self-reported</p>${report.findings.length ? report.findings.map(f => `<details class="finding ${done.has(f.id)?'done':''}"><summary><span class="dot"></span><div><div class="label">${done.has(f.id)?'Marked fixed':'Review suggested'}</div><strong>${esc(f.title)}</strong></div></summary><div class="finding-body"><p><strong>Evidence:</strong> ${esc(f.evidence)}</p><p>${esc(f.explanation)}</p><h3>What to do</h3><ol>${f.steps.map(s=>`<li>${esc(s)}</li>`).join('')}</ol><p><strong>Follow-up:</strong> ${esc(f.follow_up)}</p><button type="button" class="secondary completion" data-finding="${esc(f.id)}" aria-pressed="${done.has(f.id)}">${done.has(f.id)?'Undo completion':'Mark as fixed'}</button></div></details>`).join('') : '<p class="message">No defined rules triggered. This does not establish that your account is free of issues.</p>'}<details class="ads-section"><summary>Look at your ads (${report.ads.length})</summary>${report.ads.map(row=>{
    const ad = row.adGroupAd?.ad || {}, rsa = ad.responsiveSearchAd || {};
    return `<div class="ad"><p class="small">${esc(row.campaign?.name)} · Ad ${esc(ad.id)}</p><h3>${(rsa.headlines || []).map(h=>esc(h.text)).join(' | ') || 'Text preview unavailable for this ad format'}</h3><p>${(rsa.descriptions || []).map(d=>esc(d.text)).join(' ')}</p><p class="small">Destination: ${esc((ad.finalUrls || []).join(', '))}</p><p class="small">Spend: ${esc(amount(Number(row.metrics?.costMicros || 0)/1000000))} · Reported conversions: ${esc(row.metrics?.conversions || 0)}</p></div>`;
  }).join('')}</details><div class="limits"><strong>What this check covers</strong><p class="small">Search network settings, campaign spending without conversions, selected home-service search terms, conversion goal names, and RSA text length.</p>${report.limits.map(l=>`<p class="small">${esc(l)}</p>`).join('')}<p class="small">Generated ${esc(new Date(report.created_at).toLocaleString())}. Menu labels may vary in Google Ads.</p></div><button type="button" class="secondary print" id="print">Print / save as PDF</button>`;
  $('report').querySelectorAll('.completion').forEach(button=>button.addEventListener('click',()=>busy(button,async()=>{
    const openIds = [...$('report').querySelectorAll('details.finding')].map((node,i)=>node.open ? report.findings[i].id : null);
    const currentId = report.id;
    const updated = await api(`/api/reports/${currentId}/completion`, {finding_id:button.dataset.finding,completed:!done.has(button.dataset.finding)});
    if (report?.id !== currentId) return;
    report=updated;renderReport();
    $('report').querySelectorAll('details.finding').forEach((node,i)=>node.open=openIds.includes(report.findings[i].id));
  })));
  $('print').addEventListener('click',()=>{ $('report').querySelectorAll('details').forEach(node=>node.open=true); window.print(); });
}
boot().catch(error=>message(error.message,true));

async function loadRequests() {
  const rows = await api('/api/admin/requests');
  $('accessRequests').replaceChildren();
  for (const row of rows) {
    const item = document.createElement('div'); item.className = 'connection section';
    const label = document.createElement('p'); label.textContent = `${row.email} · ${row.business || 'Invitation'} · ${row.status}`; item.append(label);
    if (row.status === 'pending') for (const action of ['approve', 'reject']) {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'secondary'; button.textContent = action === 'approve' ? 'Approve' : 'Reject';
      button.addEventListener('click', () => busy(button, async () => { await api('/api/admin/requests', {email:row.email,action}); await loadRequests(); })); item.append(button);
    }
    $('accessRequests').append(item);
  }
}
$('inviteForm').addEventListener('submit', event => {
  event.preventDefault(); busy(event.submitter, async () => {
    const result = await api('/api/admin/requests', {email:$('inviteEmail').value,action:'invite'});
    $('inviteResult').textContent = `Copy and share this private link (expires in 7 days): ${result.url}`;
    await loadRequests();
  });
});
const invitation = new URLSearchParams(location.hash.slice(1));
if (invitation.has('invite')) { authMode(true); $('email').value = invitation.get('email') || ''; $('invitation').value = invitation.get('invite'); history.replaceState(null, '', '/'); }
