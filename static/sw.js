const CACHE_NAME = 'hilaac-v3';
const OFFLINE_URLS = [
    '/',
    '/courses/',
    '/static/manifest.json',
    '/static/images/logo-nav.webp',
    '/static/images/logo-nav.png',
    '/static/images/favicon.png',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(OFFLINE_URLS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const req = event.request;

    // Only handle GET; never intercept admin/instructor/auth/dynamic requests.
    if (req.method !== 'GET') return;

    const url = new URL(req.url);
    if (url.origin !== self.location.origin) return;
    if (
        url.pathname.startsWith('/admin-portal/') ||
        url.pathname.startsWith('/instructor/') ||
        url.pathname.startsWith('/accounts/') ||
        url.pathname.startsWith('/admin/') ||
        url.pathname.startsWith('/payments/')
    ) {
        return; // let the network handle these directly
    }

    // Network-first for page navigations to avoid stale HTML.
    if (req.mode === 'navigate') {
        event.respondWith(
            fetch(req).catch(() => caches.match(req).then((r) => r || caches.match('/')))
        );
        return;
    }

    // Cache-first for static assets, refreshing the cache in the background.
    event.respondWith(
        caches.match(req).then((cached) => {
            const networkFetch = fetch(req).then((resp) => {
                if (resp && resp.status === 200 && url.pathname.startsWith('/static/')) {
                    const copy = resp.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
                }
                return resp;
            }).catch(() => cached);
            return cached || networkFetch;
        })
    );
});
