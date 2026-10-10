// Zustand store untuk autentikasi (token + user, persist ke localStorage).
"use client";

import { create } from "zustand";

import {
  TOKEN_KEY,
  USER_KEY,
  setAuthToken,
  type User,
} from "@/lib/api";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  // True setelah loadFromStorage dijalankan (mencegah flash redirect).
  isHydrated: boolean;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
  loadFromStorage: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isHydrated: false,

  setAuth: (token, user) => {
    if (typeof window !== "undefined") {
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    }
    setAuthToken(token);
    set({ token, user, isAuthenticated: true, isHydrated: true });
  },

  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
    setAuthToken(null);
    set({ token: null, user: null, isAuthenticated: false, isHydrated: true });
  },

  loadFromStorage: () => {
    if (typeof window === "undefined") {
      set({ isHydrated: true });
      return;
    }
    const token = localStorage.getItem(TOKEN_KEY);
    const rawUser = localStorage.getItem(USER_KEY);
    let user: User | null = null;
    if (rawUser) {
      try {
        user = JSON.parse(rawUser) as User;
      } catch {
        user = null;
      }
    }
    setAuthToken(token);
    set({
      token,
      user,
      isAuthenticated: Boolean(token),
      isHydrated: true,
    });
  },
}));
