// Service worker Study Agent — cache static assets, network-first untuk API,
// cache-first untuk assets, plus offline fallback.
//
// PENTING: setiap cabang event.respondWith() HARUS selalu resolve ke Response
// yang valid. Jangan pernah mengembalikan undefined (penyebab error
// "Failed to convert value to 'Response'").
const CACHE_NAME = "study-agent-v2";
const OFFLINE_URL = "/offline";
const PRECACHE = [
  "/",
  OFFLINE_URL,
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];

function offlineResponse() {
  // Response valid sebagai fallback terakhir.
  return new Response(
    "<!doctype html><meta charset=\"utf-8\"><title>Offline</title>" +
      "<body style=\"font-family:system-ui;padding:2rem;text-align:center\">" +
      "<h1>You're offline</h1><p>Reconnect and reload to continue.</p></body>",
    { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } }
  );
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) =>
        // addAll gagal total kalau satu URL gagal; pakai allSettled agar tahan.
        Promise.allSettled(PRECACHE.map((url) => cache.add(url)))
      )
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
  const { request } = event;
  const url = new URL(request.url);

  // 1) Skip non-GET.
  if (request.method !== "GET") return;

  // 2) Skip API calls (Railway / same-origin /api) — biarkan browser handle langsung.
  if (url.hostname.includes("railway.app") || url.pathname.startsWith("/api/")) {
    return;
  }

  // 3) Skip cross-origin (mis. fonts, CDN) — jangan diintercept.
  if (url.origin !== self.location.origin) return;

  // 4) Navigation → network-first, fallback ke halaman offline.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => response)
        .catch(() =>
          caches
            .match(OFFLINE_URL)
            .then((cached) => cached || caches.match("/"))
            .then((cached) => cached || offlineResponse())
        )
    );
    return;
  }

  // 5) Static assets → cache-first, selalu kembalikan Response valid.
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request)
        .then((response) => {
          // Hanya simpan respons sukses & same-origin.
          if (response && response.ok && response.type === "basic") {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy)).catch(() => {});
          }
          return response;
        })
        .catch(() => offlineResponse());
    })
  );
});
