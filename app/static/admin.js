(()=>{
 const $=id=>document.getElementById(id);
 const esc=v=>String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
 const date=v=>String(v||'').replace('T',' ').slice(0,16);
 const themeKey='adwise_product_theme';
 const providerNames={google:'Google Ads',meta:'Meta Ads',tiktok:'TikTok Ads',google_growth:'Google Growth'};
 let csrf='',data={},loading=false;

 function setTheme(theme){
  const selected=theme==='light'?'light':'dark';
  document.documentElement.dataset.productTheme=selected;
  document.querySelectorAll('[data-theme-toggle]').forEach(button=>{button.textContent=selected==='dark'?'☀ Light':'☾ Dark';button.setAttribute('aria-pressed',String(selected==='light'))});
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content',selected==='dark'?'#05060f':'#f5f6ff');
  try{localStorage.setItem(themeKey,selected)}catch{}
 }
 try{setTheme(localStorage.getItem(themeKey)||'dark')}catch{setTheme('dark')}

 function toast(message,error=false){
  const item=document.createElement('div');item.className=`toast${error?' error-toast':''}`;item.textContent=message;$('toastRegion').append(item);setTimeout(()=>item.remove(),3600);
 }
 function setLoading(active){
  loading=active;document.body.classList.toggle('data-syncing',active);$('refreshAdmin')?.classList.toggle('loading',active);$('refreshAdmin')?.toggleAttribute('disabled',active);
 }
 async function post(url,body){
  const r=await fetch(url,{method:'POST',credentials:'same-origin',headers:{'X-CSRF-Token':csrf,'Content-Type':'application/json'},body:JSON.stringify(body||{})});
  const payload=await r.json().catch(()=>({}));if(!r.ok)throw Error(payload.detail||'Action failed');return payload;
 }
 function stateChip(ok,yes='Healthy',no='Setup required'){return `<span class="health-state ${ok?'ok':'warn'}">${esc(ok?yes:no)}</span>`}

 function renderTenants(){
  const query=$('tenantSearch').value.trim().toLowerCase(),filter=$('tenantFilter').value;
  const tenants=(data.tenants||[]).filter(t=>{
   const matchesText=!query||[t.name,t.owner_email,t.id,...(t.integrations||[]).map(i=>providerNames[i.provider]||i.provider)].join(' ').toLowerCase().includes(query);
   const matchesState=filter==='all'||(filter==='active'&&!t.tenant_paused)||(filter==='paused'&&t.tenant_paused)||(filter==='ai_paused'&&t.ai_paused);
   return matchesText&&matchesState;
  });
  $('tenantRows').innerHTML=tenants.map(t=>{
   const integrations=(t.integrations||[]).map(i=>`<span class="integration-tag" title="${esc(i.account_name||i.customer_id||'Connected')}">${esc(providerNames[i.provider]||i.provider)} · ${esc(i.status)}${i.last_sync?` · synced ${esc(date(i.last_sync))}`:''}</span>`).join('')||'<span class="muted">None</span>';
   return `<tr><td data-label="Business"><b>${esc(t.name)}</b><small>${esc(t.id)}</small></td><td data-label="Owner">${esc(t.owner_email||'—')}</td><td data-label="Usage">${esc(t.member_count)} members<br>${esc(t.campaign_count)} campaigns</td><td data-label="Integrations"><div class="integration-list">${integrations}</div></td><td data-label="Status">${stateChip(!t.tenant_paused,t.tenant_paused?'Paused':'Active',t.tenant_paused?'Paused':'Active')}${t.ai_paused?'<span class="health-state warn">AI paused</span>':''}</td><td data-label="Controls"><div class="tenant-controls"><button data-tenant="${esc(t.id)}" data-control="tenant_paused" data-state="${!t.tenant_paused}">${t.tenant_paused?'Resume tenant':'Pause tenant'}</button><button data-tenant="${esc(t.id)}" data-control="ai_paused" data-state="${!t.ai_paused}">${t.ai_paused?'Resume AI':'Pause AI'}</button></div></td><td data-label="Access"><a class="open-dashboard" href="/app?tenant=${encodeURIComponent(t.id)}">Open workspace →</a></td></tr>`;
  }).join('');
  $('tenantEmpty').classList.toggle('hidden',tenants.length>0);
 }

 function render(d){
  data=d;$('adminIdentity').textContent=d.admin.email;
  $('totals').innerHTML=Object.entries(d.totals).map(([k,v])=>`<article class="total"><span>${esc(k.replaceAll('_',' ').toUpperCase())}</span><b>${esc(v)}</b></article>`).join('');
  const p=d.platform;
  $('platformFacts').innerHTML=[['Application',p.app_name],['Production URL',p.production_url],['Hosting',p.hosting],['Region',p.region],['Database',p.database],['Deployment',p.deployment],['GitHub repository',p.repository]].map(([k,v])=>`<article><small>${esc(k)}</small><b>${esc(v)}</b></article>`).join('');
  $('apiHealth').innerHTML=d.health.apis.map(x=>`<article class="health-item"><div><b>${esc(x.name)}</b><small>${esc(x.connected_tenants)} connected tenant${x.connected_tenants===1?'':'s'}</small></div>${stateChip(x.configured,'Configured')}</article>`).join('');
  const agentStatus=Object.fromEntries(d.health.developer_agents.map(x=>[x.key,x]));
  $('aiHealth').innerHTML=d.health.ai.map(x=>`<article class="health-item"><div><b>${esc(x.name)}</b><small>Model: ${esc(x.model)}</small></div>${stateChip(x.configured,'Configured')}</article>`).join('')+`<article class="health-item"><div><b>${esc(d.health.mcp.name)}</b><small>${esc(d.health.mcp.endpoint)}</small></div>${stateChip(d.health.mcp.configured,'Secured','Token required')}</article>`+d.health.developer_agents.map(x=>`<article class="health-item"><div><b>${esc(x.name)} developer runner</b><small>Secure branch and pull-request execution</small></div>${stateChip(x.configured,'Runner ready','Runner setup required')}</article>`).join('');
  $('globalAiToggle').textContent=d.health.global_ai_paused?'Resume all AI':'Pause all AI';$('globalAiToggle').dataset.paused=String(d.health.global_ai_paused);
  const requests=d.registration_requests||[];
  $('requestCount').textContent=`${requests.filter(x=>x.status==='pending').length} pending`;
  $('requestRows').innerHTML=requests.map(x=>`<article class="request-item"><div><b>${esc(x.business_name)}</b><small>${esc(date(x.created_at))}</small></div><div>${esc(x.email)}</div><span class="status">${esc(x.status)}</span><div class="request-actions">${x.status==='pending'?`<button class="approve" data-id="${esc(x.id)}" data-decision="approve">Approve</button><button class="reject" data-id="${esc(x.id)}" data-decision="reject">Reject</button>`:''}</div></article>`).join('')||'<div class="activity-item">No registration requests.</div>';
  $('tenantCount').textContent=`${d.tenants.length} total`;renderTenants();
  $('activityRows').innerHTML=d.recent_activity.map(a=>`<article class="activity-item"><b>${esc(a.action.replaceAll('.',' / ').replaceAll('_',' '))}</b><p>${esc(a.tenant_name||'Platform')} · ${esc(a.email||'System')} · ${esc(date(a.created_at))}</p></article>`).join('')||'<div class="activity-item">No activity yet.</div>';
  $('agentRequests').innerHTML=(d.agent_requests||[]).map(x=>`<article class="agent-item"><div><b>${esc(x.agent==='codex'?'OpenAI Codex':'Anthropic Claude')}</b>${stateChip(x.status==='completed',x.status,x.status.replaceAll('_',' '))}</div><p>${esc(x.instructions)}</p><small>${esc(date(x.created_at))}${x.pull_request_url?` · <a href="${esc(x.pull_request_url)}" rel="noopener">Pull request</a>`:''}</small></article>`).join('')||'<div class="activity-item">No developer tasks queued.</div>';
  $('agentNotice').textContent=Object.values(agentStatus).some(x=>x.configured)?'Configured runners will process approved requests.':'Tasks can be saved now; execution starts after a secured runner endpoint is configured.';
  $('lastUpdated').textContent=`Updated ${new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}`;
  $('adminError').classList.add('hidden');$('adminContent').classList.remove('hidden');
 }

 async function load({quiet=false}={}){
  if(loading)return;setLoading(true);
  try{
   const boot=await fetch('/api/bootstrap',{credentials:'same-origin'}).then(r=>r.ok?r.json():Promise.reject(Error('Sign in with the Super Admin account first.')));
   csrf=boot.csrf;const r=await fetch('/api/admin/overview',{credentials:'same-origin'});if(!r.ok)throw Error(r.status===403?'Super Admin access is required.':await r.text());render(await r.json());if(!quiet)toast('Admin data refreshed.');
  }catch(e){$('adminError').textContent=e.message;$('adminError').classList.remove('hidden');toast(e.message,true)}finally{setLoading(false)}
 }
 function closeNav(){document.body.classList.remove('nav-open');$('navToggle').setAttribute('aria-expanded','false')}

 document.addEventListener('click',async e=>{
  const themeButton=e.target.closest('[data-theme-toggle]');if(themeButton){setTheme(document.documentElement.dataset.productTheme==='dark'?'light':'dark');return}
  if(e.target.closest('#navToggle')){const open=document.body.classList.toggle('nav-open');$('navToggle').setAttribute('aria-expanded',String(open));return}
  if(e.target.closest('#navBackdrop')||e.target.closest('.admin-nav a'))closeNav();
  if(e.target.closest('#refreshAdmin')){await load();return}
  const decision=e.target.closest('[data-decision]');
  if(decision){if(!confirm(`${decision.dataset.decision==='approve'?'Approve':'Reject'} this registration request?`))return;decision.disabled=true;try{await post(`/api/admin/registration-requests/${encodeURIComponent(decision.dataset.id)}/${decision.dataset.decision}`,{});toast(`Request ${decision.dataset.decision}d.`);await load({quiet:true})}catch(err){toast(err.message,true);decision.disabled=false}return}
  const control=e.target.closest('[data-control]');
  if(control){const enabled=control.dataset.state==='true',label=control.dataset.control==='tenant_paused'?'tenant':'AI';if(!confirm(`${enabled?'Pause':'Resume'} this ${label}?`))return;control.disabled=true;try{await post(`/api/admin/tenants/${encodeURIComponent(control.dataset.tenant)}/controls`,{[control.dataset.control]:enabled});toast(`${label} ${enabled?'paused':'resumed'}.`);await load({quiet:true})}catch(err){toast(err.message,true);control.disabled=false}return}
  if(e.target.id==='globalAiToggle'){const paused=e.target.dataset.paused==='true';if(!confirm(`${paused?'Resume':'Pause'} AI for every tenant?`))return;e.target.disabled=true;try{await post('/api/admin/ai-control',{paused:!paused});toast(`AI ${paused?'resumed':'paused'} for every tenant.`);await load({quiet:true})}catch(err){toast(err.message,true);e.target.disabled=false}}
 });
 $('tenantSearch').addEventListener('input',renderTenants);$('tenantFilter').addEventListener('change',renderTenants);
 $('agentRequestForm').addEventListener('submit',async e=>{e.preventDefault();const button=e.submitter;button.disabled=true;try{const result=await post('/api/admin/developer-agent-requests',{agent:$('agentChoice').value,instructions:$('agentInstructions').value});$('agentInstructions').value='';$('agentNotice').textContent=result.message;toast('Secure development task queued.');await load({quiet:true})}catch(err){toast(err.message,true)}finally{button.disabled=false}});
 if('IntersectionObserver'in window){const links=[...document.querySelectorAll('.admin-nav a[href^="#"]')],sections=links.map(link=>document.querySelector(link.getAttribute('href'))).filter(Boolean);const observer=new IntersectionObserver(entries=>{entries.filter(x=>x.isIntersecting).forEach(entry=>links.forEach(link=>link.classList.toggle('active',link.getAttribute('href')===`#${entry.target.id}`)))},{rootMargin:'-20% 0px -70%'});sections.forEach(section=>observer.observe(section))}
 load({quiet:true});if('serviceWorker'in navigator)addEventListener('load',()=>navigator.serviceWorker.register('/service-worker.js').catch(()=>{}));
})();
