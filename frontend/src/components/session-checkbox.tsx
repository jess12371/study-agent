// Kontrol status per sesi (pending / completed / skipped / rescheduled).
"use client";

import { CheckCircle2, Circle, RotateCw, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { ProgressStatus } from "@/lib/api";
import type { TranslationKey } from "@/lib/dictionary";
import { useLanguage } from "@/lib/language-context";
import { cn } from "@/lib/utils";

const STATUS_META: Record<
  ProgressStatus,
  { labelKey: TranslationKey; icon: typeof Circle; className: string }
> = {
  pending: { labelKey: "pending", icon: Circle, className: "text-muted-foreground" },
  completed: { labelKey: "completed", icon: CheckCircle2, className: "text-emerald-600" },
  skipped: { labelKey: "skipped", icon: XCircle, className: "text-zinc-400" },
  rescheduled: { labelKey: "rescheduled", icon: RotateCw, className: "text-amber-600" },
};

const OPTIONS: ProgressStatus[] = [
  "completed",
  "skipped",
  "rescheduled",
  "pending",
];

export function SessionCheckbox({
  status,
  onSelect,
  disabled,
}: {
  status: ProgressStatus;
  onSelect: (status: ProgressStatus) => void;
  disabled?: boolean;
}) {
  const { t } = useLanguage();
  const meta = STATUS_META[status];
  const Icon = meta.icon;
  const metaLabel = t(meta.labelKey);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          disabled={disabled}
          aria-label={t("sessionStatusAria", { status: metaLabel })}
          className={cn("h-7 gap-1.5 px-2", meta.className)}
        >
          <Icon className="h-4 w-4" />
          <span className="hidden text-xs font-medium sm:inline">
            {metaLabel}
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        <DropdownMenuLabel>{t("markSession")}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {OPTIONS.map((option) => {
          const optionMeta = STATUS_META[option];
          const OptionIcon = optionMeta.icon;
          return (
            <DropdownMenuItem
              key={option}
              className="cursor-pointer"
              disabled={option === status}
              onClick={() => onSelect(option)}
            >
              <OptionIcon className={cn("mr-2 h-4 w-4", optionMeta.className)} />
              {t(optionMeta.labelKey)}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
