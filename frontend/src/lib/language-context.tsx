// Language context (EN / ID / ZH) — disimpan di localStorage + helper t().
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import { dict, type Language, type TranslationKey } from "@/lib/dictionary";

export type { Language };

const STORAGE_KEY = "sa_language";

type Translate = (
  key: TranslationKey,
  vars?: Record<string, string | number>
) => string;

const LanguageContext = createContext<{
  language: Language;
  setLanguage: (language: Language) => void;
  t: Translate;
}>({
  language: "en",
  setLanguage: () => {},
  t: (key) => dict.en[key] ?? String(key),
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLang] = useState<Language>("en");

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === "en" || saved === "id" || saved === "zh") {
        setLang(saved);
      }
    } catch {
      /* localStorage bisa diblokir di mode privat / in-app browser */
    }
  }, []);

  const setLanguage = useCallback((next: Language) => {
    setLang(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* abaikan — bahasa tetap dipakai untuk sesi ini */
    }
  }, []);

  const t = useCallback<Translate>(
    (key, vars) => {
      const table = dict[language] ?? dict.en;
      const value = table[key] ?? dict.en[key];
      // Jangan pernah mengembalikan undefined: React akan melempar error
      // kalau sebuah child bukan string/angka/element yang valid.
      let text = typeof value === "string" ? value : String(key);
      if (vars) {
        for (const [name, value] of Object.entries(vars)) {
          text = text.split(`{${name}}`).join(String(value));
        }
      }
      return text;
    },
    [language]
  );

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
