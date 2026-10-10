// Hook useAuth — akses store auth + rehydrate dari localStorage saat mount.
"use client";

import { useEffect } from "react";

import { useAuthStore } from "@/lib/auth-store";

export function useAuth() {
  const state = useAuthStore();
  const { isHydrated, loadFromStorage } = state;

  useEffect(() => {
    if (!isHydrated) {
      loadFromStorage();
    }
  }, [isHydrated, loadFromStorage]);

  return state;
}
