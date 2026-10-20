// Focus Mode — Pomodoro 25 menit full-screen per sesi belajar.
"use client";

import { useEffect, useRef, useState } from "react";
import { Pause, Play, Timer, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";

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
    toast.success("Focus session complete! Session marked as completed.");
    onComplete();
  }, [finished, onComplete]);

  if (!open) return null;

  const minutes = Math.floor(remaining / 60)
    .toString()
    .padStart(2, "0");
  const seconds = (remaining % 60).toString().padStart(2, "0");
  const progress = ((total - remaining) / total) * 100;

  const handleDone = () => {
    // "Selesai" sebelum timer habis tetap menandai sesi completed.
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
        aria-label="Close focus mode"
        onClick={onClose}
        className="absolute right-6 top-6 text-muted-foreground hover:text-foreground"
      >
        <X className="h-6 w-6" />
      </button>

      <p className="flex items-center gap-2 text-sm font-medium uppercase tracking-widest text-muted-foreground">
        <Timer className="h-4 w-4" />
        Focus Mode
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
        <p className="text-sm font-medium text-emerald-600">
          Session complete — marked as Completed.
        </p>
      )}

      <div className="flex flex-wrap items-center justify-center gap-3">
        {!finished && (
          <Button variant="outline" onClick={() => setRunning((value) => !value)}>
            {running ? (
              <>
                <Pause className="h-4 w-4" />
                Pause
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                Resume
              </>
            )}
          </Button>
        )}
        <Button onClick={handleDone}>Selesai</Button>
        <Button variant="ghost" onClick={onClose}>
          Batal
        </Button>
      </div>

      <p className="max-w-sm text-xs text-muted-foreground">
        Stay on this session for {durationMinutes} minutes. When the timer ends,
        the session is marked completed automatically.
      </p>
    </div>
  );
}
