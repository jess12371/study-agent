// Panel live output saat plan di-generate via SSE (teks muncul real-time).
"use client";

import { useEffect, useRef } from "react";
import { Loader2 } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

export function PlanStreamPanel({
  status,
  text,
}: {
  status: string;
  text: string;
}) {
  const preRef = useRef<HTMLPreElement | null>(null);

  useEffect(() => {
    const node = preRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [text]);

  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardContent className="space-y-2 py-4">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Loader2 className="h-4 w-4 animate-spin" />
          {status}
        </div>
        <pre
          ref={preRef}
          className="max-h-48 overflow-y-auto whitespace-pre-wrap break-words rounded bg-background/70 p-3 text-[11px] leading-relaxed text-muted-foreground"
        >
          {text || "Waiting for the first tokens..."}
        </pre>
        <p className="text-xs text-muted-foreground">
          Live model output. Your structured plan appears when generation
          finishes.
        </p>
      </CardContent>
    </Card>
  );
}
