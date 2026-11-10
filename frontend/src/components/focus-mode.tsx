// Focus Mode — Pomodoro 25 menit full-screen per sesi belajar (multi-bahasa).
"use client";

import { useEffect, useRef, useState } from "react";
import { Pause, Play, Timer, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useLanguage } from "@/lib/language-context";

const TRANSLATIONS = {
  en: {
    focusMode: "Focus Mode",
    pause: "Pause",
    resume: "Resume",
    finish: "Finish",
    cancel: "Cancel",
    close: "Close focus mode",
    timeUp: "Time's up!",
    completed: "Session complete — marked as Completed.",
    hint: (minutes: number) =>
      `Stay on this session for ${minutes} minutes. When the timer ends, the session is marked completed automatically.`,
    toast: "Focus session complete! Session marked as completed.",
  },
  id: {
    focusMode: "Mode Fokus",
    pause: "Jeda",
    resume: "Lanjutkan",
    finish: "Selesai",
    cancel: "Batal",
    close: "Tutup mode fokus",
    timeUp: "Waktu habis!",
    completed: "Sesi selesai — ditandai Completed.",
    hint: (minutes: number) =>
      `Fokus pada sesi ini selama ${minutes} menit. Saat timer habis, sesi otomatis ditandai selesai.`,
    toast: "Sesi fokus selesai! Sesi ditandai selesai.",
  },
  zh: {
    focusMode: "专注模式",
    pause: "暂停",
    resume: "继续",
    finish: "完成",
    cancel: "取消",
    close: "关闭专注模式",
    timeUp: "时间到！",
    completed: "本次学习已完成 — 已标记为完成。",
    hint: (minutes: number) =>
      `请专注学习 ${minutes} 分钟。计时结束后，本次学习将自动标记为完成。`,
    toast: "专注时间结束！本次学习已标记为完成。",
  },
} as const;

function playBeep(): void {
  // Nada singkat via Web Audio (tanpa aset). Bisa diblokir browser sebelum gesture.
  try {
    const Ctor =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext })
        .webkitAudioContext;
    if (!Ctor) return;
    const ctx = new Ctor();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.6);
  } catch {
    /* audio opsional */
  }
}

export function FocusMode({
  open,
  topic,
  durationMinutes = 25,
  onClose,
  onComplete,
}: {
  open: boolean;
  topic: string;
  durationMinutes?: number;
  onClose: () => void;
  onComplete: () => void;
}) {
  const { language } = useLanguage();
  const t = TRANSLATIONS[language] ?? TRANSLATIONS.en;

  const total = durationMinutes * 60;
  const [remaining, setRemaining] = useState(total);
  const [running, setRunning] = useState(true);
  const [finished, setFinished] = useState(false);
  const completedRef = useRef(false);

  useEffect(() => {
    if (!open) return;
    setRemaining(total);
    setRunning(true);
    setFinished(false);
    completedRef.current = false;
  }, [open, total]);

  useEffect(() => {
    if (!open || !running || finished) return;
    const timer = window.setInterval(() => {
      setRemaining((value) => (value <= 1 ? 0 : value - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [open, running, finished]);

  useEffect(() => {
    if (remaining > 0 || finished) return;
    setFinished(true);
    setRunning(false);
  }, [remaining, finished]);

  useEffect(() => {
    if (!finished || completedRef.current) return;
    completedRef.current = true;
    playBeep();
    toast.success(t.toast);
    onComplete();
  }, [finished, onComplete, t.toast]);

  if (!open) return null;

  const minutes = Math.floor(remaining / 60)
    .toString()
    .padStart(2, "0");
  const seconds = (remaining % 60).toString().padStart(2, "0");
  const progress = ((total - remaining) / total) * 100;

  const handleDone = () => {
    // "Finish" sebelum timer habis tetap menandai sesi completed.
    if (!completedRef.current) {
      completedRef.current = true;
      onComplete();
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center gap-8 bg-background px-6 text-center">
      <button
        type="button"
        aria-label={t.close}
        onClick={onClose}
        className="absolute right-6 top-6 text-muted-foreground hover:text-foreground"
      >
        <X className="h-6 w-6" />
      </button>

      <p className="flex items-center gap-2 text-sm font-medium uppercase tracking-widest text-muted-foreground">
        <Timer className="h-4 w-4" />
        {t.focusMode}
      </p>

      <h2 className="max-w-xl text-2xl font-semibold sm:text-3xl">{topic}</h2>

      <div className="w-full max-w-md space-y-4">
        <p className="text-7xl font-bold tabular-nums sm:text-8xl">
          {minutes}:{seconds}
        </p>
        <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full bg-primary transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {finished && (
        <div className="space-y-1">
          <p className="text-lg font-semibold text-emerald-600">{t.timeUp}</p>
          <p className="text-sm font-medium text-emerald-600">{t.completed}</p>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-center gap-3">
        {!finished && (
          <Button variant="outline" onClick={() => setRunning((value) => !value)}>
            {running ? (
              <>
                <Pause className="h-4 w-4" />
                {t.pause}
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                {t.resume}
              </>
            )}
          </Button>
        )}
        <Button onClick={handleDone}>{t.finish}</Button>
        <Button variant="ghost" onClick={onClose}>
          {t.cancel}
        </Button>
      </div>

      <p className="max-w-sm text-xs text-muted-foreground">
        {t.hint(durationMinutes)}
      </p>
    </div>
  );
}
