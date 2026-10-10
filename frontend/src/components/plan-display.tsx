// Tampilan lengkap study plan (F-03): summary, milestones, jadwal, resources.
import Link from "next/link";
import { BookOpen, ExternalLink, RefreshCw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { MilestoneCard } from "@/components/milestone-card";
import { Separator } from "@/components/ui/separator";
import { WeekScheduleView } from "@/components/week-schedule";
import type {
  DaySession,
  PlanResponse,
  ProgressEntry,
  ProgressStatus,
} from "@/lib/api";

export function PlanDisplay({
  plan,
  progress,
  onMark,
  updating,
}: {
  plan: PlanResponse;
  progress?: Record<string, ProgressEntry>;
  onMark?: (
    weekNumber: number,
    session: DaySession,
    sessionIndex: number,
    status: ProgressStatus
  ) => void;
  updating?: boolean;
}) {
  return (
    <div className="space-y-8">
      {/* Summary */}
      <Card>
        <CardHeader className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle className="text-lg">Study Plan</CardTitle>
            <Badge variant="secondary">{plan.total_weeks} weeks</Badge>
            {plan.version > 1 && (
              <Badge className="gap-1">
                <RefreshCw className="h-3 w-3" />v{plan.version}
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{plan.goal_summary}</p>
        </CardContent>
      </Card>

      {/* Milestones */}
      {plan.milestones.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">Milestones</h2>
          <div className="space-y-4">
            {plan.milestones.map((milestone, index) => (
              <MilestoneCard
                key={`${milestone.month}-${index}`}
                milestone={milestone}
                index={index}
              />
            ))}
          </div>
        </section>
      )}

      <Separator />

      {/* Weekly schedule */}
      {plan.weekly_schedule.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">Weekly Schedule</h2>
          <WeekScheduleView
            weeks={plan.weekly_schedule}
            progress={progress}
            onMark={onMark}
            updating={updating}
          />
        </section>
      )}

      <Separator />

      {/* Resources */}
      {plan.resources.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">Resources</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {plan.resources.map((resource, index) => (
              <Card key={`${resource.name}-${index}`}>
                <CardContent className="space-y-2 p-4">
                  <div className="flex items-center justify-between gap-2">
                    <Badge variant="secondary" className="capitalize">
                      {resource.type}
                    </Badge>
                    {resource.for_skill && (
                      <span className="truncate text-xs text-muted-foreground">
                        {resource.for_skill}
                      </span>
                    )}
                  </div>
                  <p className="flex items-start gap-2 text-sm font-medium">
                    <BookOpen className="mt-0.5 h-4 w-4 shrink-0" />
                    {resource.name}
                  </p>
                  {resource.url && (
                    <Link
                      href={resource.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                    >
                      Open resource
                      <ExternalLink className="h-3 w-3" />
                    </Link>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
