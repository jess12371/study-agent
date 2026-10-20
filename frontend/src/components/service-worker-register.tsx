// Registrasi service worker + sinkronisasi antrean offline (client-only).
"use client";

import { useEffect } from "react";

import { registerOfflineSync } from "@/lib/offline-sync";

export function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window === "undefined") return;

    const cleanupSync = registerOfflineSync();

    if (!("serviceWorker" in navigator)) {
      return () => cleanupSync();
    }

    const register = () => {
      navigator.serviceWorker.register("/service-worker.js").catch(() => {
        /* registrasi gagal (mis. dev tanpa HTTPS) — abaikan */
      });
    };

    if (document.readyState === "complete") {
      register();
    } else {
      window.addEventListener("load", register);
    }
    return () => {
      cleanupSync();
      window.removeEventListener("load", register);
    };
  }, []);

  return null;
}
