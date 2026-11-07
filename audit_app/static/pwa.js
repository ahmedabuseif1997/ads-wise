(() => {
  if ('serviceWorker' in navigator) window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => {}));
  const button = document.getElementById('installApp');
  const hint = document.getElementById('installHint');
  let installPrompt;
  const installed = () => window.matchMedia('(display-mode: standalone)').matches || navigator.standalone;
  if (installed()) return;
  const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  if (ios) { button.classList.remove('hidden'); button.textContent = 'Add to Home Screen'; }
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault(); installPrompt = event; button.classList.remove('hidden');
  });
  button.addEventListener('click', async () => {
    if (installPrompt) {
      await installPrompt.prompt(); await installPrompt.userChoice; installPrompt = null; button.classList.add('hidden');
    } else if (ios) { hint.classList.toggle('hidden'); }
  });
  window.addEventListener('appinstalled', () => { button.classList.add('hidden'); hint.classList.add('hidden'); });
})();
