// Dialog Adaptive Reschedule (F-05): tampilkan analisis + 4 opsi, lalu apply.
"use client";

import { useCallback, useState } from "react";
import {
  CalendarClock,
  Flame,
  Loader2,
  Minimize2,
  Shuffle,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";

import { ErrorState } from "@/components/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getErrorMessage,
  rescheduleApi,
  type RescheduleAnalysis,
  type RescheduleOptionType,
  type RescheduleResult,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const OPTION_ICONS: Record<RescheduleOptionType, typeof Shuffle> = {
  REBALANCE: Shuffle,
  EXTEND: CalendarClock,
  REDUCE: Minimize2,
  INTENSIFY: Flame,
};

export function RescheduleDialog({
  planId,
  onApplied,
}: {
  planId: string;
  onApplied: (result: RescheduleResult) => void;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<RescheduleAnalysis | null>(null);
  const [selected, setSelected] = useState<RescheduleOptionType | null>(null);
  const [applying, setApplying] = useState(false);

  const loadAnalysis = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await rescheduleApi.analyze(planId);
      setAnalysis(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [planId]);

  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    if (next) {
      setSelected(null);
      setAnalysis(null);
      loadAnalysis();
    }
  };

  const handleApply = async () => {
    if (!selected) return;
    setApplying(true);
    try {
      const result = await rescheduleApi.apply(planId, {
        option_type: selected,
      });
      toast.success(`Plan updated to version v${result.version}.`);
      onApplied(result);
      setOpen(false);
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setApplying(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button>
          <Sparkles className="h-4 w-4" />
          Adapt Plan
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Adapt your study plan</DialogTitle>
          <DialogDescription>
            Pick a strategy and Study Agent will rebuild your plan while keeping
            your old version for history.
          </DialogDescription>
        </DialogHeader>

        {loading && (
          <div className="space-y-3">
            <Skeleton className="h-16 w-full rounded-lg" />
            <Skeleton className="h-24 w-full rounded-lg" />
            <Skeleton className="h-24 w-full rounded-lg" />
          </div>
        )}

        {!loading && error && (
          <ErrorState
            title="Could not analyze your plan"
            message={error}
            onRetry={loadAnalysis}
          />
        )}

        {!loading && !error && analysis && (
          <div className="space-y-4">
            <div className="rounded-lg border bg-muted/40 p-4 text-sm">
              <div className="mb-1 flex flex-wrap items-center gap-2">
                <Badge variant="secondary">
                  {Math.round(analysis.completion_rate * 100)}% complete
                </Badge>
                {analysis.weeks_behind > 0 && (
                  <Badge variant="outline">
                    {analysis.weeks_behind} week
                    {analysis.weeks_behind > 1 ? "s" : ""} behind
                  </Badge>
                )}
              </div>
              <p className="text-muted-foreground">{analysis.reason}</p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {analysis.options.map((option) => {
                const Icon = OPTION_ICONS[option.type];
                const active = selected === option.type;
                return (
                  <button
                    key={option.type}
                    type="button"
                    onClick={() => setSelected(option.type)}
                    className={cn(
                      "rounded-lg border p-4 text-left transition-colors",
                      active
                        ? "border-primary bg-primary/5 ring-1 ring-primary"
                        : "hover:border-primary/50"
                    )}
                  >
                    <div className="mb-1 flex items-center gap-2">
                      <Icon className="h-4 w-4" />
                      <span className="font-semibold">{option.title}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {option.description}
                    </p>
                    <p className="mt-2 text-xs text-amber-600">
                      Trade-off: {option.trade_offs}
                    </p>
                    {option.estimated_new_deadline && (
                      <p className="mt-1 text-xs text-muted-foreground">
                        New deadline: {option.estimated_new_deadline}
                      </p>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={applying}
          >
            Cancel
          </Button>
          <Button onClick={handleApply} disabled={!selected || applying}>
            {applying && <Loader2 className="h-4 w-4 animate-spin" />}
            Apply selected
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
