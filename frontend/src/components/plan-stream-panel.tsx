// Indikator loading saat plan di-generate (tanpa menampilkan JSON mentah).
"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

const FALLBACK_STAGES = [
  "Analyzing your goal...",
  "Designing milestones...",
  "Structuring weekly schedule...",
  "Generating resources...",
];

export function PlanStreamPanel({ status }: { status: string }) {
  // Status dari backend diprioritaskan; fallback bergantian bila masih "Starting...".
  const [fallbackIndex, setFallbackIndex] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setFallbackIndex((index) => (index + 1) % FALLBACK_STAGES.length);
    }, 8000);
    return () => window.clearInterval(timer);
  }, []);

  const label =
    status && status !== "Starting..." ? status : FALLBACK_STAGES[fallbackIndex];

  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <div className="space-y-1">
          <p className="font-medium">{label}</p>
          <p className="text-sm text-muted-foreground">
            This usually takes 1-3 minutes. Please keep this tab open.
          </p>
        </div>
        <div className="h-1.5 w-full max-w-sm overflow-hidden rounded-full bg-muted">
          <div className="h-full w-1/3 animate-pulse rounded-full bg-primary" />
        </div>
      </CardContent>
    </Card>
  );
}
