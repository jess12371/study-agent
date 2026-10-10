// Plan History (F-05 / versioning) — daftar semua versi plan, klik untuk melihat.
"use client";

import { History } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { PlanVersion } from "@/lib/api";
import { cn } from "@/lib/utils";

const REASON_LABEL: Record<string, string> = {
  initial: "Initial",
  reschedule: "Reschedule",
  regenerate: "Regenerate",
};

export function PlanHistory({
  versions,
  activeVersion,
  onSelect,
  disabled,
}: {
  versions: PlanVersion[];
  activeVersion: number;
  onSelect: (version: number) => void;
  disabled?: boolean;
}) {
  if (versions.length === 0) return null;

  return (
    <Card>
      <CardHeader className="flex-row items-center gap-2 space-y-0">
        <History className="h-4 w-4 text-muted-foreground" />
        <CardTitle className="text-base">Plan History</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {versions.map((item) => {
          const active = item.version === activeVersion;
          return (
            <button
              key={item.plan_id}
              type="button"
              disabled={disabled}
              onClick={() => onSelect(item.version)}
              className={cn(
                "flex w-full items-center justify-between gap-3 rounded-lg border px-3 py-2 text-left text-sm transition-colors",
                active
                  ? "border-primary bg-primary/5"
                  : "hover:border-primary/50",
                disabled && "cursor-not-allowed opacity-60"
              )}
            >
              <div className="flex items-center gap-2">
                <span className="font-semibold">v{item.version}</span>
                <Badge variant={item.status === "active" ? "default" : "secondary"}>
                  {item.status}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {REASON_LABEL[item.reason] ?? item.reason}
                </span>
              </div>
              <span className="text-xs text-muted-foreground">
                {new Date(item.created_at).toLocaleDateString()}
              </span>
            </button>
          );
        })}
      </CardContent>
    </Card>
  );
}
