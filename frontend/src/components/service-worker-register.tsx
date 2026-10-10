// Registrasi service worker (client-only).
"use client";

import { useEffect } from "react";

export function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;

    const register = () => {
      navigator.serviceWorker
        .register("/service-worker.js")
        .catch(() => {
          /* registrasi gagal (mis. dev tanpa HTTPS) — abaikan */
        });
    };

    if (document.readyState === "complete") {
      register();
    } else {
      window.addEventListener("load", register);
    }
    return () => window.removeEventListener("load", register);
  }, []);

  return null;
}
