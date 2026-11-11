// Tampilan error dengan tombol retry.
"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useLanguage } from "@/lib/language-context";

export function ErrorState({
  title,
  message,
  onRetry,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
}) {
  const { t } = useLanguage();
  const resolvedTitle = title ?? t("somethingWentWrong");
  const resolvedMessage = message ?? t("loadFailed");

  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-destructive/30 bg-destructive/5 px-6 py-12 text-center">
      <AlertTriangle className="h-8 w-8 text-destructive" />
      <div>
        <p className="font-semibold">{resolvedTitle}</p>
        <p className="mt-1 text-sm text-muted-foreground">{resolvedMessage}</p>
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCw className="h-4 w-4" />
          {t("tryAgain")}
        </Button>
      )}
    </div>
  );
}
