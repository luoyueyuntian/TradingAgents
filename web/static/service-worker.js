const CACHE_NAME = 'tradingagents-spa-v1';
const APP_SHELL_ASSETS = [
    '/',
    '/static/spa/index.html',
    '/static/spa/assets/app.js',
    '/static/spa/assets/index.css',
    '/static/app.webmanifest',
    '/static/icons/app-icon.svg',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL_ASSETS)).then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => Promise.all(
            keys
                .filter((key) => key !== CACHE_NAME)
                .map((key) => caches.delete(key))
        )).then(() => self.clients.claim())
    );
});

function fetchAndCache(request) {
    return fetch(request).then((response) => {
        if (!response || response.status !== 200 || response.type === 'opaque') {
            return response;
        }
        const responseToCache = response.clone();
        caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseToCache);
        });
        return response;
    });
}

self.addEventListener('fetch', (event) => {
    const { request } = event;
    if (request.method !== 'GET') {
        return;
    }

    const url = new URL(request.url);
    if (url.pathname.startsWith('/api/')) {
        return;
    }

    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request).catch(async () => {
                const cache = await caches.open(CACHE_NAME);
                return cache.match('/') || Response.error();
            })
        );
        return;
    }

    if (url.pathname.startsWith('/static/spa/')) {
        event.respondWith(
            fetchAndCache(request).catch(async () => {
                const cache = await caches.open(CACHE_NAME);
                return cache.match(request) || Response.error();
            })
        );
        return;
    }

    event.respondWith(
        caches.match(request).then((cached) => {
            if (cached) {
                return cached;
            }
            return fetchAndCache(request);
        })
    );
});
