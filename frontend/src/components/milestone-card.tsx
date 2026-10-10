// Card per milestone pada study plan.
import { Flag, Target } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Milestone } from "@/lib/api";

export function MilestoneCard({
  milestone,
  index,
}: {
  milestone: Milestone;
  index: number;
}) {
  return (
    <div className="relative pl-8">
      {/* Garis timeline + titik */}
      <span className="absolute left-0 top-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
        {index + 1}
      </span>
      <Card>
        <CardHeader className="space-y-1 pb-3">
          <div className="flex items-center justify-between gap-3">
            <CardTitle className="text-base">
              Month {milestone.month}
            </CardTitle>
            <Badge variant="secondary" className="shrink-0">
              Milestone {index + 1}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p className="flex items-start gap-2">
            <Target className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
            <span>
              <span className="font-medium">Focus: </span>
              {milestone.focus}
            </span>
          </p>
          <p className="text-muted-foreground">
            <span className="font-medium text-foreground">Target: </span>
            {milestone.target}
          </p>
          <p className="flex items-start gap-2 text-muted-foreground">
            <Flag className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              <span className="font-medium text-foreground">Checkpoint: </span>
              {milestone.checkpoint}
            </span>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
