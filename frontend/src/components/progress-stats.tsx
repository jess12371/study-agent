// Ringkasan progres plan (F-04): completion rate, jam belajar, streak, counts.
"use client";

import { useCallback, useEffect, useState } from "react";
import { Flame, RotateCcw } from "lucide-react";
import { toast } from "sonner";

import { ErrorState } from "@/components/error-state";
import { RescheduleDialog } from "@/components/reschedule-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getErrorMessage,
  progressApi,
  type ProgressStats,
  type RescheduleResult,
} from "@/lib/api";

export function ProgressStatsCard({
  planId,
  refreshKey,
  onReset,
  onRescheduled,
}: {
  planId: string;
  refreshKey: number;
  onReset?: () => void;
  onRescheduled?: (result: RescheduleResult) => void;
}) {
  const [stats, setStats] = useState<ProgressStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setStats(await progressApi.stats(planId));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [planId]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats, refreshKey]);

  const handleReset = async () => {
    if (typeof window !== "undefined" && !window.confirm("Reset all progress for this plan?")) {
      return;
    }
    try {
      await progressApi.reset(planId);
      toast.success("Progress reset.");
      await fetchStats();
      onReset?.();
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  if (loading) {
    return <Skeleton className="h-40 w-full rounded-xl" />;
  }

  if (error || !stats) {
    return (
      <ErrorState
        title="Failed to load progress"
        message={error ?? "Unknown error"}
        onRetry={fetchStats}
      />
    );
  }

  const percent = Math.round(stats.completion_rate * 100);
  const marked = stats.completed + stats.skipped;
  const fallingBehind = marked > 0 && stats.completion_rate < 0.8;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-lg">Your Progress</CardTitle>
        <Button variant="ghost" size="sm" onClick={handleReset} className="text-muted-foreground">
          <RotateCcw className="h-4 w-4" />
          Reset
        </Button>
      </CardHeader>
      <CardContent className="space-y-5">
        {fallingBehind && (
          <div className="flex flex-col gap-3 rounded-lg border border-amber-500/40 bg-amber-500/5 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-medium">
                You&apos;re behind schedule ({percent}% complete)
              </p>
              <p className="text-sm text-muted-foreground">
                Want to adapt your plan to get back on track?
              </p>
            </div>
            <RescheduleDialog planId={planId} onApplied={onRescheduled ?? (() => {})} />
          </div>
        )}

        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Completion rate</span>
            <span className="font-semibold">{percent}%</span>
          </div>
          <Progress value={percent} />
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-lg border p-3 text-center">
            <p className="text-xl font-semibold">{stats.total_hours}</p>
            <p className="text-xs text-muted-foreground">Hours studied</p>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <p className="flex items-center justify-center gap-1 text-xl font-semibold">
              <Flame className="h-4 w-4 text-orange-500" />
              {stats.current_streak}
            </p>
            <p className="text-xs text-muted-foreground">Current streak</p>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <p className="text-xl font-semibold">{stats.longest_streak}</p>
            <p className="text-xs text-muted-foreground">Longest streak</p>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <p className="text-xl font-semibold">{stats.total_sessions}</p>
            <p className="text-xs text-muted-foreground">Total sessions</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-4 text-sm">
          <span className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-600" />
            <span className="text-muted-foreground">
              Completed <span className="font-medium text-foreground">{stats.completed}</span>
            </span>
          </span>
          <span className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-zinc-400" />
            <span className="text-muted-foreground">
              Skipped <span className="font-medium text-foreground">{stats.skipped}</span>
            </span>
          </span>
          <span className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-muted-foreground" />
            <span className="text-muted-foreground">
              Pending <span className="font-medium text-foreground">{stats.pending}</span>
            </span>
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
