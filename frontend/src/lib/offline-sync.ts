// Sinkronisasi progres yang diantrikan saat offline (Background Sync fallback).
"use client";

import { toast } from "sonner";

import { progressApi } from "@/lib/api";
import { getQueue, removeQueued } from "@/lib/offline-db";

let flushing = false;

export async function flushProgressQueue(): Promise<number> {
  if (typeof navigator !== "undefined" && !navigator.onLine) return 0;
  if (flushing) return 0;
  flushing = true;
  let synced = 0;
  try {
    const queue = await getQueue();
    for (const item of queue) {
      try {
        await progressApi.mark(item.planId, item.payload);
        await removeQueued(item.id);
        synced += 1;
      } catch {
        // Masih offline / server error → hentikan, coba lagi nanti.
        break;
      }
    }
  } finally {
    flushing = false;
  }
  if (synced > 0) {
    toast.success(`${synced} offline change${synced > 1 ? "s" : ""} synced.`);
  }
  return synced;
}

export async function requestBackgroundSync(): Promise<void> {
  // Minta SW melakukan background sync (didukung Chrome/Android).
  try {
    if ("serviceWorker" in navigator) {
      const registration = await navigator.serviceWorker.ready;
      const sync = (registration as ServiceWorkerRegistration & {
        sync?: { register: (tag: string) => Promise<void> };
      }).sync;
      await sync?.register("sync-progress");
    }
  } catch {
    /* Safari tidak mendukung Background Sync — fallback ke event "online". */
  }
}

export function registerOfflineSync(): () => void {
  if (typeof window === "undefined") return () => {};

  const handleOnline = () => {
    void flushProgressQueue();
  };
  const handleMessage = (event: MessageEvent) => {
    if (event.data?.type === "flush-progress") void flushProgressQueue();
  };

  window.addEventListener("online", handleOnline);
  navigator.serviceWorker?.addEventListener("message", handleMessage);

  // Coba flush saat aplikasi dibuka (kalau online).
  if (navigator.onLine) void flushProgressQueue();

  return () => {
    window.removeEventListener("online", handleOnline);
    navigator.serviceWorker?.removeEventListener("message", handleMessage);
  };
}
