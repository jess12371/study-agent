// Banner "Install App" untuk PWA (muncul setelah beberapa kali kunjungan).
"use client";

import { useEffect, useState } from "react";
import { Download, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { usePwaInstall } from "@/hooks/use-pwa-install";

const VISITS_KEY = "sa_visits";
const DISMISS_KEY = "sa_pwa_dismissed";

export function PwaInstallPrompt() {
  const { canInstall, installed, promptInstall } = usePwaInstall();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (localStorage.getItem(DISMISS_KEY) === "1") return;

    const visits = Number(localStorage.getItem(VISITS_KEY) ?? "0") + 1;
    localStorage.setItem(VISITS_KEY, String(visits));
    // Tampilkan kalau installable dan user sudah membuka app minimal 2x.
    if (visits >= 2) setVisible(true);
  }, []);

  if (!visible || !canInstall || installed) return null;

  const handleInstall = async () => {
    const outcome = await promptInstall();
    if (outcome === "accepted" || outcome === "dismissed") setVisible(false);
  };

  const handleLater = () => {
    localStorage.setItem(DISMISS_KEY, "1");
    setVisible(false);
  };

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 p-3 sm:left-auto sm:right-4 sm:w-96">
      <div className="flex items-start gap-3 rounded-xl border bg-background p-4 shadow-lg">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
          <Download className="h-4 w-4 text-primary" />
        </span>
        <div className="flex-1 space-y-2">
          <p className="text-sm font-medium">Install Study Agent</p>
          <p className="text-xs text-muted-foreground">
            Add it to your home screen for a full-screen, app-like experience.
          </p>
          <div className="flex gap-2">
            <Button size="sm" onClick={handleInstall}>
              Install App
            </Button>
            <Button size="sm" variant="ghost" onClick={handleLater}>
              Later
            </Button>
          </div>
        </div>
        <button
          type="button"
          aria-label="Dismiss"
          onClick={handleLater}
          className="text-muted-foreground hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
