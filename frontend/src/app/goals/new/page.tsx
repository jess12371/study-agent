// Onboarding form untuk membuat goal baru (multi-step, validasi zod per step).
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, ArrowRight, Check, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Navbar } from "@/components/navbar";
import { ProtectedRoute } from "@/components/protected-route";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Slider } from "@/components/ui/slider";
import { goalsApi, getErrorMessage } from "@/lib/api";
import type { TranslationKey } from "@/lib/dictionary";
import { useLanguage } from "@/lib/language-context";

import {
  LEVEL_OPTIONS,
  STUDY_TIME_OPTIONS,
  TOTAL_STEPS,
  WORK_DAY_OPTIONS,
  useGoalForm,
} from "./use-goal-form";

const STEP_TITLE_KEYS: TranslationKey[] = [
  "step1Title",
  "step2Title",
  "step3Title",
  "step4Title",
];

const LEVEL_KEYS: Record<string, TranslationKey> = {
  None: "levelNone",
  Beginner: "levelBeginner",
  Intermediate: "levelIntermediate",
  Advanced: "levelAdvanced",
};

const STUDY_TIME_KEYS: Record<string, TranslationKey> = {
  morning: "studyMorning",
  afternoon: "studyAfternoon",
  evening: "studyEvening",
  flexible: "studyFlexible",
};

const DAY_KEYS: Record<string, TranslationKey> = {
  monday: "dayMonday",
  tuesday: "dayTuesday",
  wednesday: "dayWednesday",
  thursday: "dayThursday",
  friday: "dayFriday",
  saturday: "daySaturday",
  sunday: "daySunday",
};

const ERROR_KEYS: Record<string, TranslationKey> = {
  "Topic is required.": "validationTopic",
  "Select your current level.": "validationLevel",
  "Target is required.": "validationTarget",
  "Enter a whole number of months.": "validationDeadline",
  "At least 1 month.": "validationDeadline",
  "At most 36 months.": "validationDeadline",
  "Select at least one working day.": "validationWorkDays",
  "Select a preferred study time.": "validationStudyTime",
};

function FieldError({ message }: { message?: string }) {
  const { t } = useLanguage();
  if (!message) return null;
  const key = ERROR_KEYS[message];
  return (
    <p className="text-sm font-medium text-destructive">
      {key ? t(key) : message}
    </p>
  );
}

function GoalForm() {
  const router = useRouter();
  const { t } = useLanguage();
  const {
    step,
    data,
    errors,
    setField,
    toggleWorkDay,
    nextStep,
    prevStep,
    reset,
  } = useGoalForm();
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const goal = await goalsApi.create({ ...data });
      toast.success(t("goalCreated"));
      reset();
      router.push(`/goals/${goal.id}`);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium">
            {t("stepOf", { step, total: TOTAL_STEPS })}
          </span>
          <span className="text-muted-foreground">
            {t(STEP_TITLE_KEYS[step - 1])}
          </span>
        </div>
        <Progress value={(step / TOTAL_STEPS) * 100} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">
            {t(STEP_TITLE_KEYS[step - 1])}
          </CardTitle>
          <CardDescription>
            {step === 4 ? t("reviewDesc") : t("stepDesc")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Step 1 */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="topic">{t("topic")}</Label>
                <Input
                  id="topic"
                  placeholder={t("topicPlaceholder")}
                  value={data.topic}
                  onChange={(e) => setField("topic", e.target.value)}
                />
                <FieldError message={errors.topic} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="level">{t("currentLevel")}</Label>
                <Select
                  value={data.current_level}
                  onValueChange={(value) => setField("current_level", value)}
                >
                  <SelectTrigger id="level">
                    <SelectValue placeholder={t("selectLevel")} />
                  </SelectTrigger>
                  <SelectContent>
                    {LEVEL_OPTIONS.map((level) => (
                      <SelectItem key={level} value={level}>
                        {t(LEVEL_KEYS[level] ?? "levelNone")}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldError message={errors.current_level} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="target">{t("target")}</Label>
                <Input
                  id="target"
                  placeholder={t("targetPlaceholder")}
                  value={data.target}
                  onChange={(e) => setField("target", e.target.value)}
                />
                <FieldError message={errors.target} />
              </div>
            </div>
          )}

          {/* Step 2 */}
          {step === 2 && (
            <div className="space-y-2">
              <Label htmlFor="deadline">{t("deadlineMonthsLabel")}</Label>
              <Input
                id="deadline"
                type="number"
                min={1}
                max={36}
                value={data.deadline_months}
                onChange={(e) =>
                  setField("deadline_months", Number(e.target.value))
                }
              />
              <FieldError message={errors.deadline_months} />
              <p className="text-sm text-muted-foreground">
                {t("deadlineHint")}
              </p>
            </div>
          )}

          {/* Step 3 */}
          {step === 3 && (
            <div className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="work-start">{t("workStarts")}</Label>
                  <Input
                    id="work-start"
                    type="time"
                    value={data.work_hours_start}
                    onChange={(e) => setField("work_hours_start", e.target.value)}
                  />
                  <FieldError message={errors.work_hours_start} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="work-end">{t("workEnds")}</Label>
                  <Input
                    id="work-end"
                    type="time"
                    value={data.work_hours_end}
                    onChange={(e) => setField("work_hours_end", e.target.value)}
                  />
                  <FieldError message={errors.work_hours_end} />
                </div>
              </div>

              <div className="space-y-2">
                <Label>{t("workingDays")}</Label>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {WORK_DAY_OPTIONS.map((day) => (
                    <label
                      key={day}
                      className="flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm"
                    >
                      <Checkbox
                        checked={data.work_days.includes(day)}
                        onCheckedChange={() => toggleWorkDay(day)}
                      />
                      {t(DAY_KEYS[day])}
                    </label>
                  ))}
                </div>
                <FieldError message={errors.work_days} />
              </div>

              <div className="space-y-2">
                <Label>{t("preferredStudyTime")}</Label>
                <RadioGroup
                  value={data.preferred_study_time}
                  onValueChange={(value) =>
                    setField("preferred_study_time", value)
                  }
                  className="grid grid-cols-2 gap-2 sm:grid-cols-4"
                >
                  {STUDY_TIME_OPTIONS.map((option) => (
                    <label
                      key={option}
                      className="flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm"
                    >
                      <RadioGroupItem value={option} />
                      {t(STUDY_TIME_KEYS[option])}
                    </label>
                  ))}
                </RadioGroup>
                <FieldError message={errors.preferred_study_time} />
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>{t("maxSession")}</Label>
                  <span className="text-sm font-medium">
                    {t("maxSessionMin", {
                      minutes: data.max_session_minutes,
                    })}
                  </span>
                </div>
                <Slider
                  min={30}
                  max={240}
                  step={15}
                  value={[data.max_session_minutes]}
                  onValueChange={(value) =>
                    setField("max_session_minutes", value[0] ?? 60)
                  }
                />
                <FieldError message={errors.max_session_minutes} />
              </div>
            </div>
          )}

          {/* Step 4 */}
          {step === 4 && (
            <div className="space-y-4">
              <div className="grid gap-3 text-sm">
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">{t("topic")}</span>
                  <span className="text-right font-medium">{data.topic}</span>
                </div>
                <Separator />
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">
                    {t("currentLevel")}
                  </span>
                  <span className="text-right font-medium">
                    {t(LEVEL_KEYS[data.current_level] ?? "levelNone")}
                  </span>
                </div>
                <Separator />
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">{t("target")}</span>
                  <span className="text-right font-medium">{data.target}</span>
                </div>
                <Separator />
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">
                    {t("deadlineMonthsLabel")}
                  </span>
                  <span className="text-right font-medium">
                    {t(
                      data.deadline_months > 1
                        ? "deadlineMonthsPlural"
                        : "deadlineMonths",
                      { count: data.deadline_months }
                    )}
                  </span>
                </div>
                <Separator />
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">
                    {t("workStarts")} – {t("workEnds")}
                  </span>
                  <span className="text-right font-medium">
                    {data.work_hours_start}–{data.work_hours_end}
                  </span>
                </div>
                <Separator />
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">
                    {t("workingDays")}
                  </span>
                  <div className="flex flex-wrap justify-end gap-1">
                    {[...data.work_days]
                      .sort(
                        (a, b) =>
                          WORK_DAY_OPTIONS.indexOf(a as never) -
                          WORK_DAY_OPTIONS.indexOf(b as never)
                      )
                      .map((day) => (
                        <Badge key={day} variant="secondary">
                          {t(DAY_KEYS[day])}
                        </Badge>
                      ))}
                  </div>
                </div>
                <Separator />
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">
                    {t("preferredStudyTime")}
                  </span>
                  <span className="text-right font-medium">
                    {t(STUDY_TIME_KEYS[data.preferred_study_time])}
                  </span>
                </div>
                <Separator />
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">
                    {t("maxSession")}
                  </span>
                  <span className="text-right font-medium">
                    {t("maxSessionMin", {
                      minutes: data.max_session_minutes,
                    })}
                  </span>
                </div>
              </div>
            </div>
          )}

          <Separator />

          <div className="flex items-center justify-between gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={prevStep}
              disabled={step === 1 || submitting}
            >
              <ArrowLeft className="h-4 w-4" />
              {t("back")}
            </Button>

            {step < TOTAL_STEPS ? (
              <Button type="button" onClick={() => nextStep()}>
                {t("next")}
                <ArrowRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button type="button" onClick={handleSubmit} disabled={submitting}>
                {submitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Check className="h-4 w-4" />
                )}
                {t("createGoalButton")}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function NewGoalPage() {
  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-muted/20">
        <Navbar />
        <main className="container py-10">
          <GoalForm />
        </main>
      </div>
    </ProtectedRoute>
  );
}
