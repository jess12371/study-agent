// Card hasil Feasibility Check (F-02).
import { AlertTriangle, CheckCircle2, Info, Loader2, RefreshCw, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import type { FeasibilityResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

const VERDICT_STYLES: Record<
  FeasibilityResponse["verdict"],
  { label: string; className: string; icon: typeof CheckCircle2 }
> = {
  REALISTIC: {
    label: "Realistic",
    className: "border-transparent bg-emerald-600 text-white hover:bg-emerald-600",
    icon: CheckCircle2,
  },
  REALISTIC_WITH_NOTES: {
    label: "Realistic with notes",
    className: "border-transparent bg-amber-500 text-white hover:bg-amber-500",
    icon: AlertTriangle,
  },
  UNREALISTIC: {
    label: "Unrealistic",
    className: "border-transparent bg-red-600 text-white hover:bg-red-600",
    icon: XCircle,
  },
};

export function FeasibilityCard({
  feasibility,
  onRescope,
  rescoping,
}: {
  feasibility: FeasibilityResponse;
  onRescope?: () => void;
  rescoping?: boolean;
}) {
  const style = VERDICT_STYLES[feasibility.verdict];
  const Icon = style.icon;

  return (
    <Card>
      <CardHeader className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-lg">Feasibility Check</CardTitle>
          <Badge className={cn("gap-1", style.className)}>
            <Icon className="h-3.5 w-3.5" />
            {style.label}
          </Badge>
        </div>
        <div className="space-y-1">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>Confidence</span>
            <span className="font-medium text-foreground">
              {Math.round(feasibility.confidence * 100)}%
            </span>
          </div>
          <Progress value={feasibility.confidence * 100} />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-3 text-center">
          <div className="rounded-lg border p-3">
            <p className="text-xl font-semibold">{feasibility.required_hours}</p>
            <p className="text-xs text-muted-foreground">Required hours</p>
          </div>
          <div className="rounded-lg border p-3">
            <p className="text-xl font-semibold">{feasibility.available_hours}</p>
            <p className="text-xs text-muted-foreground">Available hours</p>
          </div>
          <div className="rounded-lg border p-3">
            <p
              className={cn(
                "text-xl font-semibold",
                feasibility.gap_hours > 0 ? "text-red-600" : "text-emerald-600"
              )}
            >
              {feasibility.gap_hours > 0 ? "+" : ""}
              {feasibility.gap_hours}
            </p>
            <p className="text-xs text-muted-foreground">Gap hours</p>
          </div>
        </div>

        <Separator />

        <div className="space-y-1">
          <p className="text-sm font-medium">Analysis</p>
          <p className="text-sm text-muted-foreground">{feasibility.analysis}</p>
        </div>

        {feasibility.recommendations.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium">Recommendations</p>
            <ul className="space-y-1.5">
              {feasibility.recommendations.map((rec, index) => (
                <li
                  key={index}
                  className="flex gap-2 text-sm text-muted-foreground"
                >
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <Info className="h-3.5 w-3.5" />
          <span>
            Source: {feasibility.benchmark_source || "estimate"}
          </span>
          {feasibility.requires_manual_review && (
            <Badge variant="outline" className="text-amber-600">
              Needs manual review
            </Badge>
          )}
        </div>

        {!feasibility.feasible && onRescope && (
          <div className="space-y-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3">
            <p className="text-sm text-muted-foreground">
              This target is not realistic with your current deadline. Let the AI
              propose a realistic target and deadline, then re-run the check.
            </p>
            <Button onClick={onRescope} disabled={rescoping} className="w-full">
              {rescoping ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              Re-scope Goal &amp; Deadline
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
