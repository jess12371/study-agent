// Detail goal — jalankan Feasibility Check (F-02) lalu Generate Plan (F-03).
"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowLeft,
  CalendarDays,
  Loader2,
  Sparkles,
  Wand2,
} from "lucide-react";
import { toast } from "sonner";

import { ChatPanel } from "@/components/chat-panel";
import { ErrorState } from "@/components/error-state";
import { ExportMenu } from "@/components/export-menu";
import { FeasibilityCard } from "@/components/feasibility-card";
import { Navbar } from "@/components/navbar";
import { PlanDisplay } from "@/components/plan-display";
import { PlanHistory } from "@/components/plan-history";
import { PlanProgress } from "@/components/plan-progress";
import { ProgressStatsCard } from "@/components/progress-stats";
import { ResourceRecommendations } from "@/components/resource-recommendations";
import { ProtectedRoute } from "@/components/protected-route";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  feasibilityApi,
  getErrorMessage,
  goalsApi,
  plansApi,
  progressApi,
  progressSessionKey,
  type DaySession,
  type FeasibilityRequest,
  type FeasibilityResponse,
  type Goal,
  type PlanResponse,
  type PlanVersion,
  type ProgressEntry,
  type ProgressStatus,
  type RescheduleResult,
} from "@/lib/api";

function toFeasibilityRequest(goal: Goal): FeasibilityRequest {
  return {
    topic: goal.topic,
    current_level: goal.current_level || "unspecified",
    target: goal.target || goal.topic,
    deadline_months: goal.deadline_months || 1,
    work_hours_start: goal.work_hours_start || "09:00",
    work_hours_end: goal.work_hours_end || "18:00",
    work_days: goal.work_days || [],
    preferred_study_time: goal.preferred_study_time || "evening",
    max_session_minutes: goal.max_session_minutes || 60,
    unavailable_days: goal.unavailable_days || [],
  };
}

function GoalDetail() {
  const params = useParams<{ id: string }>();
  const goalId = params.id;

  const [goal, setGoal] = useState<Goal | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [feasibility, setFeasibility] = useState<FeasibilityResponse | null>(null);
  const [checking, setChecking] = useState(false);

  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [generating, setGenerating] = useState(false);

  const [progressByKey, setProgressByKey] = useState<
    Record<string, ProgressEntry>
  >({});
  const [statsRefresh, setStatsRefresh] = useState(0);
  const [updatingProgress, setUpdatingProgress] = useState(false);
  const [history, setHistory] = useState<PlanVersion[]>([]);
  const [switchingVersion, setSwitchingVersion] = useState(false);

  const loadHistory = useCallback(async () => {
    try {
      setHistory(await plansApi.history(goalId));
    } catch {
      /* history opsional */
    }
  }, [goalId]);

  const loadGoal = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await goalsApi.get(goalId);
      setGoal(data);
      // Muat plan terbaru kalau sudah ada, supaya refresh tidak kehilangan plan.
      try {
        const existingPlan = await plansApi.getByGoal(goalId);
        setPlan(existingPlan);
      } catch {
        /* belum ada plan untuk goal ini */
      }
      loadHistory();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [goalId, loadHistory]);

  useEffect(() => {
    loadGoal();
  }, [loadGoal]);
  // Muat entry progres begitu plan tersedia.
  useEffect(() => {
    if (!plan) return;
    let active = true;
    progressApi
      .list(plan.plan_id)
      .then((entries) => {
        if (!active) return;
        const map: Record<string, ProgressEntry> = {};
        for (const entry of entries) {
          if (entry.week_number == null || entry.day_name == null) continue;
          map[
            progressSessionKey(
              entry.week_number,
              entry.day_name,
              entry.session_index
            )
          ] = entry;
        }
        setProgressByKey(map);
      })
      .catch(() => {
        /* biarkan kosong; error akan tampil saat mark */
      });
    return () => {
      active = false;
    };
  }, [plan]);

  const runFeasibility = async () => {
    if (!goal) return;
    setChecking(true);
    try {
      const result = await feasibilityApi.check(toFeasibilityRequest(goal));
      setFeasibility(result);
      toast.success("Feasibility check complete.");
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setChecking(false);
    }
  };

  const generatePlan = async () => {
    setGenerating(true);
    try {
      const result = await plansApi.generate({
        goal_id: goalId,
        feasibility_result: feasibility ?? undefined,
      });
      setPlan(result);
      setProgressByKey({});
      setStatsRefresh((n) => n + 1);
      await loadHistory();
      toast.success("Study plan generated!");
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setGenerating(false);
    }
  };

  const handleMark = async (
    weekNumber: number,
    session: DaySession,
    sessionIndex: number,
    status: ProgressStatus
  ) => {
    if (!plan) return;
    const key = progressSessionKey(weekNumber, session.day, sessionIndex);
    const previous = progressByKey[key];

    // Optimistic update.
    const optimistic: ProgressEntry = {
      id: previous?.id ?? `optimistic-${key}`,
      plan_id: plan.plan_id,
      week_number: weekNumber,
      day_name: session.day,
      session_index: sessionIndex,
      status,
      actual_duration:
        status === "completed"
          ? session.duration_minutes ?? previous?.actual_duration ?? null
          : previous?.actual_duration ?? null,
      difficulty_rating: previous?.difficulty_rating ?? null,
      notes: previous?.notes ?? null,
      scheduled_at: previous?.scheduled_at ?? null,
      completed_at:
        status === "completed" ? new Date().toISOString() : null,
    };
    setProgressByKey((map) => ({ ...map, [key]: optimistic }));
    setUpdatingProgress(true);

    try {
      const saved = await progressApi.mark(plan.plan_id, {
        week_number: weekNumber,
        day_name: session.day,
        session_index: sessionIndex,
        status,
        actual_duration:
          status === "completed" ? session.duration_minutes : undefined,
      });
      setProgressByKey((map) => ({ ...map, [key]: saved }));
      setStatsRefresh((n) => n + 1);
    } catch (err) {
      // Rollback kalau gagal.
      setProgressByKey((map) => {
        const next = { ...map };
        if (previous) next[key] = previous;
        else delete next[key];
        return next;
      });
      toast.error(getErrorMessage(err));
    } finally {
      setUpdatingProgress(false);
    }
  };

  const handleSelectVersion = async (version: number) => {
    if (plan?.version === version) return;
    setSwitchingVersion(true);
    try {
      const selected = await plansApi.getByGoal(goalId, version);
      setPlan(selected);
      setProgressByKey({});
      setStatsRefresh((n) => n + 1);
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSwitchingVersion(false);
    }
  };

  const handleRescheduled = async (result: RescheduleResult) => {
    // Muat plan versi baru lalu reset tampilan progres (plan baru = mulai bersih).
    try {
      const newPlan = await plansApi.getById(result.plan_id);
      setPlan(newPlan);
      setProgressByKey({});
      setStatsRefresh((n) => n + 1);
      await loadHistory();
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-32 w-full rounded-xl" />
        <Skeleton className="h-48 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  if (error || !goal) {
    return (
      <ErrorState
        title="Goal not found"
        message={error ?? "This goal does not exist or isn't yours."}
        onRetry={loadGoal}
      />
    );
  }

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link href="/dashboard">
          <ArrowLeft className="h-4 w-4" />
          Back to dashboard
        </Link>
      </Button>

      {/* Goal info */}
      <Card>
        <CardHeader className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <CardTitle className="text-2xl">{goal.topic}</CardTitle>
              {goal.target && (
                <p className="text-muted-foreground">{goal.target}</p>
              )}
            </div>
            <Badge variant="secondary" className="capitalize">
              {goal.status}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex flex-wrap gap-x-6 gap-y-2 text-muted-foreground">
            <span className="flex items-center gap-2">
              <CalendarDays className="h-4 w-4" />
              {goal.deadline_months
                ? `${goal.deadline_months} month${goal.deadline_months > 1 ? "s" : ""}`
                : "No deadline"}
            </span>
            <span>
              Level: <span className="font-medium text-foreground">{goal.current_level || "—"}</span>
            </span>
            <span>
              Study time: <span className="font-medium text-foreground capitalize">{goal.preferred_study_time || "—"}</span>
            </span>
            <span>
              Session: <span className="font-medium text-foreground">{goal.max_session_minutes ?? "—"} min</span>
            </span>
            {goal.work_hours_start && goal.work_hours_end && (
              <span>
                Work: <span className="font-medium text-foreground">{goal.work_hours_start}–{goal.work_hours_end}</span>
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Feasibility */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold">Feasibility Check</h2>
          <Button
            onClick={runFeasibility}
            disabled={checking}
            variant={feasibility ? "outline" : "default"}
          >
            {checking ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {feasibility ? "Re-run check" : "Run Feasibility Check"}
          </Button>
        </div>

        {feasibility ? (
          <FeasibilityCard feasibility={feasibility} />
        ) : (
          <Card className="border-dashed">
            <CardContent className="py-8 text-center text-sm text-muted-foreground">
              Run the feasibility check to see if this goal is realistic.
            </CardContent>
          </Card>
        )}
      </section>

      {plan && (
        <>
          <Separator />
          {/* Progress (F-04) */}
          <section className="space-y-4">
            <h2 className="text-xl font-semibold">Your Progress</h2>
            <ProgressStatsCard
              planId={plan.plan_id}
              refreshKey={statsRefresh}
              onReset={() => {
                setProgressByKey({});
                setStatsRefresh((n) => n + 1);
              }}
              onRescheduled={handleRescheduled}
            />
          </section>
        </>
      )}

      {history.length > 0 && (
        <>
          <Separator />
          {/* Plan History (versioning) */}
          <section className="space-y-4">
            <PlanHistory
              versions={history}
              activeVersion={plan?.version ?? 0}
              onSelect={handleSelectVersion}
              disabled={switchingVersion || generating}
            />
          </section>
        </>
      )}

      <Separator />

      {/* Plan */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold">Study Plan</h2>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              onClick={generatePlan}
              disabled={generating || (!feasibility && !plan)}
              title={
                !feasibility && !plan
                  ? "Run the feasibility check first"
                  : undefined
              }
            >
              {generating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Wand2 className="h-4 w-4" />
              )}
              {plan ? "Regenerate Plan" : "Generate Plan"}
            </Button>
            {plan && <ExportMenu planId={plan.plan_id} />}
          </div>
        </div>

        {!feasibility && !plan && (
          <p className="text-sm text-muted-foreground">
            Run the feasibility check first to unlock plan generation.
          </p>
        )}

        {generating && <PlanProgress active />}

        {plan && !generating ? (
          <PlanDisplay
            plan={plan}
            progress={progressByKey}
            onMark={handleMark}
            updating={updatingProgress}
          />
        ) : (
          !generating &&
          feasibility && (
            <Card className="border-dashed">
              <CardContent className="py-8 text-center text-sm text-muted-foreground">
                Generate a study plan to see milestones, a weekly schedule, and
                resources.
              </CardContent>
            </Card>
          )
        )}
      </section>

      {plan && (
        <>
          <Separator />
          {/* Recommended Resources (F-06) */}
          <section className="space-y-4">
            <h2 className="text-xl font-semibold">
              Recommended Resources for Your Goal
            </h2>
            <ResourceRecommendations planId={plan.plan_id} />
          </section>
        </>
      )}

      {goal && (
        <>
          <Separator />
          {/* Agent Dialog (F-11) */}
          <section className="space-y-4">
            <h2 className="text-xl font-semibold">Chat with Study Agent</h2>
            <ChatPanel goalId={goalId} onPlanUpdated={loadGoal} />
          </section>
        </>
      )}
    </div>
  );
}

export default function GoalDetailPage() {
  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-muted/20">
        <Navbar />
        <main className="container py-10">
          <GoalDetail />
        </main>
      </div>
    </ProtectedRoute>
  );
}
