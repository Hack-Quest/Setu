const CACHE_NAME = "setu-cache-v3";
const IS_LOCAL_DEV = self.location.hostname === "127.0.0.1" || self.location.hostname === "localhost";

const urlsToCache = [
    "/",
    "/landing.html",
    "/css/shared.css",
    "/js/utils.js",
    "/js/api.js"
];

self.addEventListener("install", (event) => {
    if (IS_LOCAL_DEV) {
        self.skipWaiting();
        return;
    }

    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(urlsToCache))
    );
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil((async () => {
        const cacheNames = await caches.keys();
        await Promise.all(cacheNames.map((name) => caches.delete(name)));

        if (IS_LOCAL_DEV) {
            await self.registration.unregister();
            const clients = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
            await Promise.all(clients.map((client) => client.navigate(client.url)));
            return;
        }

        await self.clients.claim();
    })());
});

self.addEventListener("fetch", (event) => {
    if (IS_LOCAL_DEV) {
        event.respondWith(fetch(event.request));
        return;
    }

    event.respondWith(
        caches.match(event.request).then((response) => response || fetch(event.request))
    );
});
