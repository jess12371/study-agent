// Halaman offline fallback (di-cache service worker).
import Link from "next/link";
import { WifiOff } from "lucide-react";

import { Button } from "@/components/ui/button";

export const metadata = {
  title: "Offline — Study Agent",
};

export default function OfflinePage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-muted/30 px-6 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
        <WifiOff className="h-7 w-7 text-primary" />
      </div>
      <h1 className="text-2xl font-semibold">You&apos;re offline</h1>
      <p className="max-w-sm text-sm text-muted-foreground">
        Study Agent needs a connection for AI features. Check your network and
        try again — cached pages are still available.
      </p>
      <Button asChild>
        <Link href="/">Try again</Link>
      </Button>
    </div>
  );
}
