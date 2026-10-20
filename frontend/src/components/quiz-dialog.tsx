// Quiz Me — 3 soal pilihan ganda dari topik sesi jadwal (F-Tutor).
"use client";

import { useState } from "react";
import { Brain, CheckCircle2, Loader2, RotateCcw, Save, XCircle } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getErrorMessage,
  quizApi,
  tutorApi,
  type QuizQuestion,
} from "@/lib/api";
import { cn } from "@/lib/utils";

export function QuizDialog({
  planId,
  weekNumber,
  dayName,
}: {
  planId: string;
  weekNumber: number;
  dayName: string;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [quizTopic, setQuizTopic] = useState("");
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [score, setScore] = useState(0);
  const [finished, setFinished] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const loadQuiz = async () => {
    setLoading(true);
    setSaved(false);
    try {
      const data = await tutorApi.quiz(planId, weekNumber, dayName);
      setQuestions(data.questions);
      setQuizTopic(data.topic);
      setIndex(0);
      setSelected(null);
      setScore(0);
      setFinished(false);
    } catch (err) {
      toast.error(getErrorMessage(err));
      setOpen(false);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    if (next) void loadQuiz();
  };

  const current = questions[index];
  const answered = selected !== null;

  const choose = (optionIndex: number) => {
    if (answered || !current) return;
    setSelected(optionIndex);
    if (optionIndex === current.correct_index) setScore((value) => value + 1);
  };

  const next = () => {
    if (index + 1 >= questions.length) {
      setFinished(true);
    } else {
      setIndex((value) => value + 1);
      setSelected(null);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await quizApi.submit({
        plan_id: planId,
        week_number: weekNumber,
        day_name: dayName,
        score,
        total_questions: questions.length,
      });
      setSaved(true);
      toast.success("Quiz score saved!");
      window.setTimeout(() => {
        setOpen(false);
        setSaved(false);
      }, 1300);
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline">
          <Brain className="h-4 w-4" />
          Quiz Me
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            Quiz Me
          </DialogTitle>
          <DialogDescription>
            {quizTopic ? `Topic: ${quizTopic}` : "Generating questions from your schedule..."}
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-6 w-3/4" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : finished ? (
          <div className="space-y-4 py-4 text-center">
            <p className="text-4xl font-bold">
              {score}/{questions.length}
            </p>
            <p className="text-sm text-muted-foreground">
              {score === questions.length
                ? "Perfect score — excellent work!"
                : "Keep practicing. Review the explanations and try again."}
            </p>

            {saved ? (
              <div className="flex flex-col items-center gap-2 py-2 text-emerald-600 animate-in fade-in zoom-in duration-300">
                <CheckCircle2 className="h-9 w-9" />
                <p className="font-medium">Skor tersimpan!</p>
              </div>
            ) : (
              <div className="flex flex-col justify-center gap-2 sm:flex-row">
                <Button onClick={handleSave} disabled={saving}>
                  {saving ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4" />
                  )}
                  Simpan Hasil &amp; Selesai
                </Button>
                <Button onClick={loadQuiz} variant="outline" disabled={saving}>
                  <RotateCcw className="h-4 w-4" />
                  Try again
                </Button>
              </div>
            )}
          </div>
        ) : current ? (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Question {index + 1} of {questions.length}
            </p>
            <p className="font-medium">{current.question}</p>

            <div className="space-y-2">
              {current.options.map((option, optionIndex) => {
                const isCorrect = optionIndex === current.correct_index;
                const isSelected = optionIndex === selected;
                return (
                  <button
                    key={optionIndex}
                    type="button"
                    disabled={answered}
                    onClick={() => choose(optionIndex)}
                    className={cn(
                      "flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors",
                      !answered && "hover:border-primary/60",
                      answered && isCorrect && "border-emerald-500 bg-emerald-500/10",
                      answered &&
                        isSelected &&
                        !isCorrect &&
                        "border-red-500 bg-red-500/10",
                      answered && !isCorrect && !isSelected && "opacity-60"
                    )}
                  >
                    {answered && isCorrect && (
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
                    )}
                    {answered && isSelected && !isCorrect && (
                      <XCircle className="h-4 w-4 shrink-0 text-red-600" />
                    )}
                    <span>{option}</span>
                  </button>
                );
              })}
            </div>

            {answered && (
              <div className="rounded-lg border bg-muted/40 p-3 text-sm">
                <span className="font-medium">Explanation: </span>
                {current.explanation}
              </div>
            )}

            <div className="flex justify-end">
              <Button onClick={next} disabled={!answered}>
                {index + 1 >= questions.length ? "See results" : "Next"}
              </Button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No questions available.</p>
        )}
      </DialogContent>
    </Dialog>
  );
}
