// Error boundary untuk halaman goal detail. Menampilkan UI yang bisa dipulihkan
// alih-alih layar putih "Application error" saat ada plan/cache yang korup.
"use client";

import Link from "next/link";
import { useEffect } from "react";
import { AlertTriangle, RefreshCw, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useLanguage } from "@/lib/language-context";

export default function GoalDetailError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const { t } = useLanguage();

  useEffect(() => {
    console.error("[goal-detail] render error:", error);
  }, [error]);

  const clearCacheAndReload = async () => {
    try {
      if ("caches" in window) {
        const keys = await caches.keys();
        await Promise.all(keys.map((key) => caches.delete(key)));
      }
      if ("serviceWorker" in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations();
        await Promise.all(registrations.map((reg) => reg.unregister()));
      }
    } catch {
      /* cache/service worker opsional — tetap reload */
    }
    window.location.reload();
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-muted/20 px-6 text-center">
      <span className="flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10">
        <AlertTriangle className="h-7 w-7 text-destructive" />
      </span>
      <h1 className="text-2xl font-semibold">{t("planLoadErrorTitle")}</h1>
      <p className="max-w-md text-sm text-muted-foreground">
        {t("planLoadErrorDesc")}
      </p>
      <div className="flex flex-wrap items-center justify-center gap-2">
        <Button onClick={reset}>
          <RefreshCw className="h-4 w-4" />
          {t("tryAgain")}
        </Button>
        <Button variant="outline" onClick={clearCacheAndReload}>
          <Trash2 className="h-4 w-4" />
          {t("clearCacheReload")}
        </Button>
        <Button variant="ghost" asChild>
          <Link href="/dashboard">{t("backToDashboard")}</Link>
        </Button>
      </div>
    </div>
  );
}
