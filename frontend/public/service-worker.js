// Service worker Study Agent — cache static assets, network-first untuk API,
// cache-first untuk assets, plus offline fallback.
const CACHE_NAME = "study-agent-v1";
const OFFLINE_URL = "/offline";
const PRECACHE = [
  "/",
  OFFLINE_URL,
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // API calls: network-first (same-origin only).
  if (url.origin === self.location.origin && url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(request).catch(() => caches.match(request))
    );
    return;
  }

  // Hanya tangani request same-origin (assets/precache).
  if (url.origin !== self.location.origin) return;

  // Navigation: network-first dengan offline fallback.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match(OFFLINE_URL).then((response) => response || caches.match("/"))
      )
    );
    return;
  }

  // Assets: cache-first, lalu simpan salinannya.
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches
            .open(CACHE_NAME)
            .then((cache) => cache.put(request, copy))
            .catch(() => {});
          return response;
        })
        .catch(() => cached);
    })
  );
});
