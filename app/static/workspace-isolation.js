(() => {
  const renderSeo = seo;
  seo = function isolatedSeo() {
    renderSeo();
    const workspace = state.workspace;
    const metrics = workspace?.growth_metrics;
    const selected = metrics?.search_console;
    if (workspace?.integrations?.google_growth?.status !== 'connected') return;
    const picker = `<div class="panel panel-pad" style="margin-bottom:18px">
      <form id="searchConsolePropertyForm" class="form-fields">
        <label>Exact Search Console property
          <input name="site_url" value="${esc(selected?.site_url || '')}" placeholder="https://example.com/ or sc-domain:example.com" required>
        </label>
        <button class="secondary" type="submit">Verify & assign to this workspace</button>
      </form>
      <p class="sub">Other Search Console profiles are never listed in this workspace.</p>
    </div>`;
    const current = document.getElementById('searchConsolePropertyForm');
    if (current) current.closest('.panel').outerHTML = picker;
    else document.getElementById('viewContent').insertAdjacentHTML('afterbegin', picker);
  };

  document.addEventListener('submit', async event => {
    if (event.target.id !== 'businessAccountForm') return;
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target).entries());
    try {
      state.workspace.growth_metrics = await req(
        `/api/workspaces/${encodeURIComponent(state.tenant)}/integrations/google-growth/business-account`,
        'POST', data);
      render();
      toast('Business Profile assigned to this workspace.');
    } catch (error) {
      toast(error.message, true);
    }
  });
})();
