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

import {
  LEVEL_OPTIONS,
  STUDY_TIME_OPTIONS,
  TOTAL_STEPS,
  WORK_DAY_OPTIONS,
  useGoalForm,
} from "./use-goal-form";

const STEP_TITLES = [
  "What do you want to learn?",
  "When do you want to reach it?",
  "Your availability",
  "Review & confirm",
];

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="text-sm font-medium text-destructive">{message}</p>;
}

function GoalForm() {
  const router = useRouter();
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
      toast.success("Goal created! Let's check if it's realistic.");
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
            Step {step} of {TOTAL_STEPS}
          </span>
          <span className="text-muted-foreground">{STEP_TITLES[step - 1]}</span>
        </div>
        <Progress value={(step / TOTAL_STEPS) * 100} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">{STEP_TITLES[step - 1]}</CardTitle>
          <CardDescription>
            {step === 4
              ? "Make sure everything looks right, then create your goal."
              : "Fill in the details below to build your personalized plan."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Step 1 */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="topic">Topic</Label>
                <Input
                  id="topic"
                  placeholder="e.g. Mandarin Chinese"
                  value={data.topic}
                  onChange={(e) => setField("topic", e.target.value)}
                />
                <FieldError message={errors.topic} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="level">Current level</Label>
                <Select
                  value={data.current_level}
                  onValueChange={(value) => setField("current_level", value)}
                >
                  <SelectTrigger id="level">
                    <SelectValue placeholder="Select your current level" />
                  </SelectTrigger>
                  <SelectContent>
                    {LEVEL_OPTIONS.map((level) => (
                      <SelectItem key={level} value={level}>
                        {level}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldError message={errors.current_level} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="target">Target</Label>
                <Input
                  id="target"
                  placeholder='e.g. "HSK 4 score 250"'
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
              <Label htmlFor="deadline">Deadline (months)</Label>
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
                Between 1 and 36 months.
              </p>
            </div>
          )}

          {/* Step 3 */}
          {step === 3 && (
            <div className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="work-start">Work starts</Label>
                  <Input
                    id="work-start"
                    type="time"
                    value={data.work_hours_start}
                    onChange={(e) => setField("work_hours_start", e.target.value)}
                  />
                  <FieldError message={errors.work_hours_start} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="work-end">Work ends</Label>
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
                <Label>Working days</Label>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {WORK_DAY_OPTIONS.map((day) => (
                    <label
                      key={day}
                      className="flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm capitalize"
                    >
                      <Checkbox
                        checked={data.work_days.includes(day)}
                        onCheckedChange={() => toggleWorkDay(day)}
                      />
                      {day}
                    </label>
                  ))}
                </div>
                <FieldError message={errors.work_days} />
              </div>

              <div className="space-y-2">
                <Label>Preferred study time</Label>
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
                      className="flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm capitalize"
                    >
                      <RadioGroupItem value={option} />
                      {option}
                    </label>
                  ))}
                </RadioGroup>
                <FieldError message={errors.preferred_study_time} />
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Max session length</Label>
                  <span className="text-sm font-medium">
                    {data.max_session_minutes} min
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
                  <span className="text-muted-foreground">Topic</span>
                  <span className="text-right font-medium">{data.topic}</span>
                </div>
                <Separator />
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Current level</span>
                  <span className="text-right font-medium">
                    {data.current_level}
                  </span>
                </div>
                <Separator />
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Target</span>
                  <span className="text-right font-medium">{data.target}</span>
                </div>
                <Separator />
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Deadline</span>
                  <span className="text-right font-medium">
                    {data.deadline_months} month
                    {data.deadline_months > 1 ? "s" : ""}
                  </span>
                </div>
                <Separator />
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Work hours</span>
                  <span className="text-right font-medium">
                    {data.work_hours_start}–{data.work_hours_end}
                  </span>
                </div>
                <Separator />
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Working days</span>
                  <div className="flex flex-wrap justify-end gap-1">
                    {[...data.work_days].sort(
                      (a, b) =>
                        WORK_DAY_OPTIONS.indexOf(a as never) -
                        WORK_DAY_OPTIONS.indexOf(b as never)
                    ).map((day) => (
                      <Badge key={day} variant="secondary" className="capitalize">
                        {day.slice(0, 3)}
                      </Badge>
                    ))}
                  </div>
                </div>
                <Separator />
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">
                    Preferred study time
                  </span>
                  <span className="text-right font-medium capitalize">
                    {data.preferred_study_time}
                  </span>
                </div>
                <Separator />
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">
                    Max session length
                  </span>
                  <span className="text-right font-medium">
                    {data.max_session_minutes} min
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
              Back
            </Button>

            {step < TOTAL_STEPS ? (
              <Button type="button" onClick={() => nextStep()}>
                Next
                <ArrowRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button type="button" onClick={handleSubmit} disabled={submitting}>
                {submitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Check className="h-4 w-4" />
                )}
                Create Goal
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
