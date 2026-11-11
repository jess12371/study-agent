// Dashboard — daftar goals user (butuh login).
"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Plus } from "lucide-react";

import { ErrorState } from "@/components/error-state";
import { GoalCard } from "@/components/goal-card";
import { Navbar } from "@/components/navbar";
import { ProtectedRoute } from "@/components/protected-route";
import { QuizStats } from "@/components/quiz-stats";
import { TutorDrawer } from "@/components/tutor-drawer";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { goalsApi, type Goal } from "@/lib/api";
import { useAuth } from "@/lib/hooks/use-auth";
import { useLanguage } from "@/lib/language-context";

function GoalsSection() {
  const { t } = useLanguage();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchGoals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await goalsApi.list();
      setGoals(data);
    } catch {
      setError(t("couldNotLoadGoals"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchGoals();
  }, [fetchGoals]);

  if (loading) {
    return (
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-40 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (error) {
    return <ErrorState title={t("failedLoadGoals")} message={error} onRetry={fetchGoals} />;
  }

  if (goals.length === 0) {
    return (
      <Card className="border-dashed">
        <CardHeader className="items-center text-center">
          <CardTitle className="text-xl">{t("noGoalsTitle")}</CardTitle>
          <CardDescription>{t("noGoalsDesc")}</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center">
          <Button asChild>
            <Link href="/goals/new">
              <Plus className="h-4 w-4" />
              {t("createNewGoal")}
            </Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {goals.map((goal) => (
        <GoalCard key={goal.id} goal={goal} />
      ))}
    </div>
  );
}

function DashboardContent() {
  const { user } = useAuth();
  const { t } = useLanguage();

  return (
    <div className="min-h-screen bg-muted/20">
      <Navbar />
      <main className="container space-y-8 py-10">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              {t("welcomeUser", {
                name: user?.name || user?.email || "Learner",
              })}
            </h1>
            <p className="text-muted-foreground">{t("dashboardSubtitle")}</p>
          </div>
          <Button asChild>
            <Link href="/goals/new">
              <Plus className="h-4 w-4" />
              {t("createNewGoal")}
            </Link>
          </Button>
        </div>

        <section className="space-y-4">
          <h2 className="text-xl font-semibold">{t("yourGoals")}</h2>
          <GoalsSection />
        </section>

        <section className="space-y-4">
          <h2 className="text-xl font-semibold">{t("quizStatsTitle")}</h2>
          <QuizStats />
        </section>
      </main>
      <TutorDrawer />
    </div>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
