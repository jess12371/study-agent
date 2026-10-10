// Card ringkas untuk menampilkan satu goal di dashboard.
import Link from "next/link";
import { CalendarDays, Target } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { Goal } from "@/lib/api";

export function GoalCard({ goal }: { goal: Goal }) {
  return (
    <Link href={`/goals/${goal.id}`} className="block">
      <Card className="h-full transition-shadow hover:shadow-md">
        <CardHeader className="space-y-2">
          <div className="flex items-start justify-between gap-3">
            <CardTitle className="text-lg leading-tight">{goal.topic}</CardTitle>
            <Badge
              variant={
                goal.status === "active"
                  ? "default"
                  : goal.status === "archived"
                    ? "secondary"
                    : "outline"
              }
              className="shrink-0 capitalize"
            >
              {goal.status}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          {goal.target && (
            <p className="flex items-start gap-2">
              <Target className="mt-0.5 h-4 w-4 shrink-0" />
              <span className="line-clamp-2">{goal.target}</span>
            </p>
          )}
          <p className="flex items-center gap-2">
            <CalendarDays className="h-4 w-4 shrink-0" />
            {goal.deadline_months
              ? `${goal.deadline_months} month${goal.deadline_months > 1 ? "s" : ""} deadline`
              : "No deadline set"}
          </p>
        </CardContent>
      </Card>
    </Link>
  );
}
