// Indikator progres bertahap saat generate plan (estimasi waktu, bukan SSE).
"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

// Tahapan perkiraan berdasarkan detik berjalan.
const STAGES: { label: string; until: number }[] = [
  { label: "Analyzing your goal...", until: 10 },
  { label: "Designing milestones...", until: 25 },
  { label: "Building weekly schedule...", until: 60 },
  { label: "Selecting resources...", until: Number.POSITIVE_INFINITY },
];

const ESTIMATED_SECONDS = 45;

export function PlanProgress({ active }: { active: boolean }) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    if (!active) {
      setSeconds(0);
      return;
    }
    const timer = setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => clearInterval(timer);
  }, [active]);

  if (!active) return null;

  const stage = STAGES.find((item) => seconds < item.until) ?? STAGES[STAGES.length - 1];
  // Progress "merayap" sampai 95% (langsung 100% saat selesai/berpindah).
  const percent = Math.min(95, Math.round((seconds / ESTIMATED_SECONDS) * 100) + 5);

  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardContent className="space-y-3 py-6">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Loader2 className="h-4 w-4 animate-spin" />
          {stage.label}
        </div>
        <Progress value={percent} />
        <p className="text-xs text-muted-foreground">
          This usually takes 1-3 minutes. Please keep this tab open.
        </p>
      </CardContent>
    </Card>
  );
}
