// Spinner + teks untuk state loading.
import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

export function Loading({
  text = "Loading...",
  className,
}: {
  text?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground",
        className
      )}
    >
      <Loader2 className="h-6 w-6 animate-spin" />
      <p className="text-sm">{text}</p>
    </div>
  );
}
