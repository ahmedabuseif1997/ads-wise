// Cache only a generic offline page. Never cache authenticated pages or API data.
const CACHE = 'adswise-audit-offline-v1';
const OFFLINE = '/assets/offline.html';
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll([OFFLINE, "/assets/audit.css"])));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('adswise-audit-offline-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  if (event.request.method === 'GET' && new URL(event.request.url).origin === self.location.origin && new URL(event.request.url).pathname === '/assets/audit.css') {
    event.respondWith(fetch(event.request).catch(() => caches.match('/assets/audit.css')));
    return;
  }
  if (event.request.method !== 'GET' || new URL(event.request.url).origin !== self.location.origin || event.request.mode !== 'navigate') return;
  event.respondWith(fetch(event.request).catch(async () => (await caches.match(OFFLINE)) || Response.error()));
});
