// "Your Quiz Stats" — total, rata-rata, skor terbaik, dan riwayat quiz terakhir.
"use client";

import { useCallback, useEffect, useState } from "react";
import { Brain, Target, Trophy } from "lucide-react";

import { ErrorState } from "@/components/error-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getErrorMessage, quizApi, type QuizHistory } from "@/lib/api";
import { cn } from "@/lib/utils";

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Brain;
  label: string;
  value: string | number;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 py-5">
        <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
          <Icon className="h-5 w-5 text-primary" />
        </span>
        <div>
          <p className="text-2xl font-semibold">{value}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export function QuizStats() {
  const [data, setData] = useState<QuizHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await quizApi.history());
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="grid gap-3 sm:grid-cols-3">
        {[0, 1, 2].map((index) => (
          <Skeleton key={index} className="h-20 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Could not load quiz stats"
        message={error}
        onRetry={load}
      />
    );
  }

  if (!data || data.total_quizzes === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          No quizzes yet. Open a study plan, pick a session, and click{" "}
          <span className="font-medium text-foreground">Quiz Me</span> to start
          tracking your scores.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard icon={Brain} label="Total quizzes" value={data.total_quizzes} />
        <StatCard
          icon={Target}
          label="Average score"
          value={`${data.average_score}%`}
        />
        <StatCard
          icon={Trophy}
          label="Best score"
          value={`${data.best_score}%`}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent attempts</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {data.attempts.slice(0, 5).map((attempt) => {
            const percentage = attempt.total_questions
              ? Math.round((attempt.score / attempt.total_questions) * 100)
              : 0;
            return (
              <div key={attempt.id} className="space-y-1">
                <div className="flex items-center justify-between gap-2 text-sm">
                  <span className="truncate">
                    {attempt.goal_topic ?? "Study plan"} · Week{" "}
                    {attempt.week_number} · {attempt.day_name}
                  </span>
                  <span className="shrink-0 font-medium">
                    {attempt.score}/{attempt.total_questions} · {percentage}%
                  </span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className={cn(
                      "h-full",
                      percentage >= 80
                        ? "bg-emerald-600"
                        : percentage >= 50
                          ? "bg-amber-500"
                          : "bg-red-500"
                    )}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
                <p className="text-[10px] text-muted-foreground">
                  {new Date(attempt.created_at).toLocaleString()}
                </p>
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}
