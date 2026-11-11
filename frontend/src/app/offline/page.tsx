// Halaman offline fallback (di-cache service worker).
"use client";

import Link from "next/link";
import { WifiOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useLanguage } from "@/lib/language-context";

export default function OfflinePage() {
  const { t } = useLanguage();

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-muted/30 px-6 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
        <WifiOff className="h-7 w-7 text-primary" />
      </div>
      <h1 className="text-2xl font-semibold">{t("offlineTitle")}</h1>
      <p className="max-w-sm text-sm text-muted-foreground">
        {t("offlineDesc")}
      </p>
      <Button asChild>
        <Link href="/">{t("tryAgain")}</Link>
      </Button>
    </div>
  );
}
