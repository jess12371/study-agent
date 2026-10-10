// Zustand store untuk form onboarding goal (multi-step) + validasi zod per step.
"use client";

import { create } from "zustand";
import { z } from "zod";

export const WORK_DAY_OPTIONS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
] as const;

export const LEVEL_OPTIONS = ["None", "Beginner", "Intermediate", "Advanced"];

export const STUDY_TIME_OPTIONS = ["morning", "afternoon", "evening", "flexible"];

export const TOTAL_STEPS = 4;

const TIME_REGEX = /^\d{2}:\d{2}$/;

// --- Skema per step ---
export const step1Schema = z.object({
  topic: z.string().min(1, "Topic is required.").max(200),
  current_level: z.string().min(1, "Select your current level."),
  target: z.string().min(1, "Target is required.").max(300),
});

export const step2Schema = z.object({
  deadline_months: z.coerce
    .number()
    .int("Enter a whole number of months.")
    .min(1, "At least 1 month.")
    .max(36, "At most 36 months."),
});

export const step3Schema = z.object({
  work_hours_start: z.string().regex(TIME_REGEX, "Invalid start time."),
  work_hours_end: z.string().regex(TIME_REGEX, "Invalid end time."),
  work_days: z.array(z.string()).min(1, "Select at least one working day."),
  preferred_study_time: z.string().min(1, "Select a preferred study time."),
  max_session_minutes: z.number().min(30, "Minimum 30 minutes.").max(240, "Maximum 240 minutes."),
});

export interface GoalFormData {
  topic: string;
  current_level: string;
  target: string;
  deadline_months: number;
  work_hours_start: string;
  work_hours_end: string;
  work_days: string[];
  preferred_study_time: string;
  max_session_minutes: number;
}

const INITIAL_DATA: GoalFormData = {
  topic: "",
  current_level: "",
  target: "",
  deadline_months: 3,
  work_hours_start: "09:00",
  work_hours_end: "18:00",
  work_days: ["monday", "tuesday", "wednesday", "thursday", "friday"],
  preferred_study_time: "evening",
  max_session_minutes: 60,
};

const STEP_SCHEMAS: Record<number, z.ZodTypeAny> = {
  1: step1Schema,
  2: step2Schema,
  3: step3Schema,
};

interface GoalFormState {
  step: number;
  data: GoalFormData;
  errors: Record<string, string>;
  setField: <K extends keyof GoalFormData>(field: K, value: GoalFormData[K]) => void;
  toggleWorkDay: (day: string) => void;
  validateStep: (step: number) => boolean;
  nextStep: () => boolean;
  prevStep: () => void;
  reset: () => void;
}

export const useGoalForm = create<GoalFormState>((set, get) => ({
  step: 1,
  data: INITIAL_DATA,
  errors: {},

  setField: (field, value) =>
    set((state) => ({
      data: { ...state.data, [field]: value },
      errors: { ...state.errors, [field]: undefined as unknown as string },
    })),

  toggleWorkDay: (day) =>
    set((state) => {
      const selected = state.data.work_days.includes(day)
        ? state.data.work_days.filter((d) => d !== day)
        : [...state.data.work_days, day];
      return { data: { ...state.data, work_days: selected } };
    }),

  validateStep: (step) => {
    const schema = STEP_SCHEMAS[step];
    if (!schema) {
      set({ errors: {} });
      return true;
    }
    const result = schema.safeParse(get().data);
    if (result.success) {
      set({ errors: {} });
      return true;
    }
    const errors: Record<string, string> = {};
    for (const issue of result.error.issues) {
      const key = String(issue.path[0] ?? "form");
      if (!errors[key]) errors[key] = issue.message;
    }
    set({ errors });
    return false;
  },

  nextStep: () => {
    const { step, validateStep } = get();
    if (!validateStep(step)) return false;
    set({ step: Math.min(step + 1, TOTAL_STEPS) });
    return true;
  },

  prevStep: () => set((state) => ({ step: Math.max(state.step - 1, 1) })),

  reset: () => set({ step: 1, data: INITIAL_DATA, errors: {} }),
}));
