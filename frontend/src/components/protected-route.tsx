// Wrapper halaman yang butuh login — redirect ke /login kalau belum auth.
"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { Loading } from "@/components/loading";
import { useAuth } from "@/lib/hooks/use-auth";

export function ProtectedRoute({
  children,
  fallback,
}: {
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { isAuthenticated, isHydrated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isHydrated && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isHydrated, isAuthenticated, router]);

  if (!isHydrated || !isAuthenticated) {
    return fallback ?? <Loading text="Checking your session..." />;
  }

  return <>{children}</>;
}
