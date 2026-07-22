/* Offline support for ספר המתכונים של גל.
   - app shell + index.json: network first, cache as backup  -> updates arrive immediately
   - page images + icons:    cache first                     -> instant and available offline
   - recipes.json (14 MB):   never cached, it is only a fallback path
   Bump VERSION whenever the shell changes. */
const VERSION = 'v3';
const CACHE = 'gal-recipes-' + VERSION;
const SHELL = [
  './', './index.html', './index.json', './tips.json', './manifest.json',
  './icon-32.png', './icon-180.png', './icon-192.png', './icon-512.png'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => Promise.allSettled(SHELL.map(u => c.add(u))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if(req.method !== 'GET') return;

  const url = new URL(req.url);
  if(url.origin !== self.location.origin) return;          // CDN scripts + GitHub API: leave alone
  if(url.pathname.endsWith('recipes.json')) return;        // too big to cache
  if(url.pathname.endsWith('notes.json')) return;          // user data, never cache

  const isAsset = /\.(jpg|jpeg|png|svg|webp)$/i.test(url.pathname);

  if(isAsset){
    // cache first
    e.respondWith(
      caches.match(req).then(hit => hit || fetch(req).then(res => {
        if(res && res.ok){
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy));
        }
        return res;
      }))
    );
    return;
  }

  // network first for the app shell and index.json
  e.respondWith(
    fetch(req).then(res => {
      if(res && res.ok){
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(req, copy));
      }
      return res;
    }).catch(() =>
      caches.match(req).then(hit => hit || caches.match('./index.html'))
    )
  );
});
