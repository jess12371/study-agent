// Dashboard — daftar goals user (butuh login).
"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Plus } from "lucide-react";

import { ErrorState } from "@/components/error-state";
import { GoalCard } from "@/components/goal-card";
import { Navbar } from "@/components/navbar";
import { ProtectedRoute } from "@/components/protected-route";
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

function GoalsSection() {
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
      setError("Could not load your goals. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

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
    return <ErrorState title="Failed to load goals" message={error} onRetry={fetchGoals} />;
  }

  if (goals.length === 0) {
    return (
      <Card className="border-dashed">
        <CardHeader className="items-center text-center">
          <CardTitle className="text-xl">No goals yet</CardTitle>
          <CardDescription>
            Create your first goal to generate a personalized study plan.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center">
          <Button asChild>
            <Link href="/goals/new">
              <Plus className="h-4 w-4" />
              Create New Goal
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

  return (
    <div className="min-h-screen bg-muted/20">
      <Navbar />
      <main className="container space-y-8 py-10">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Welcome, {user?.name || user?.email || "Learner"}
            </h1>
            <p className="text-muted-foreground">
              Here are your learning goals and study plans.
            </p>
          </div>
          <Button asChild>
            <Link href="/goals/new">
              <Plus className="h-4 w-4" />
              Create New Goal
            </Link>
          </Button>
        </div>

        <section className="space-y-4">
          <h2 className="text-xl font-semibold">Your Goals</h2>
          <GoalsSection />
        </section>
      </main>
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
