// Axios API client + typed endpoints untuk Study Agent backend.
import axios, { AxiosError } from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export { API_URL };

export const TOKEN_KEY = "sa_token";
export const USER_KEY = "sa_user";

// --- Tipe data ---
export interface User {
  id: string;
  email: string;
  name?: string | null;
  is_active: boolean;
  is_verified?: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Goal {
  id: string;
  user_id: string;
  topic: string;
  current_level?: string | null;
  target?: string | null;
  deadline_months?: number | null;
  work_hours_start?: string | null;
  work_hours_end?: string | null;
  work_days?: string[] | null;
  preferred_study_time?: string | null;
  max_session_minutes?: number | null;
  unavailable_days?: string[] | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface GoalCreate {
  topic: string;
  current_level: string;
  target: string;
  deadline_months: number;
  work_hours_start: string;
  work_hours_end: string;
  work_days: string[];
  preferred_study_time: string;
  max_session_minutes: number;
  unavailable_days?: string[];
}

export interface FeasibilityRequest {
  topic: string;
  current_level: string;
  target: string;
  deadline_months: number;
  work_hours_start: string;
  work_hours_end: string;
  work_days: string[];
  preferred_study_time: string;
  max_session_minutes: number;
  unavailable_days?: string[];
  language?: "en" | "id" | "zh";
}

export interface RescopeSuggestion {
  target: string;
  deadline_months: number;
  rationale: string;
  changes: string[];
}

export interface FeasibilityResponse {
  feasible: boolean;
  confidence: number;
  required_hours: number;
  available_hours: number;
  gap_hours: number;
  verdict: "REALISTIC" | "REALISTIC_WITH_NOTES" | "UNREALISTIC";
  analysis: string;
  recommendations: string[];
  benchmark_source?: string | null;
  requires_manual_review: boolean;
}

export interface Resource {
  type: string;
  name: string;
  url?: string | null;
  for_skill?: string | null;
}

export interface Milestone {
  month: number;
  focus: string;
  target: string;
  checkpoint: string;
}

export interface DaySession {
  day: string;
  date_offset: number;
  time: string;
  topic: string;
  duration_minutes: number;
  activities: string[];
  resources: Resource[];
}

export interface WeekSchedule {
  week: number;
  theme: string;
  days: DaySession[];
}

export interface PlanResponse {
  plan_id: string;
  goal_summary: string;
  total_weeks: number;
  milestones: Milestone[];
  weekly_schedule: WeekSchedule[];
  resources: Resource[];
  created_at: string;
  version: number;
  status: string;
  reason: string;
}

export interface PlanVersion {
  plan_id: string;
  version: number;
  status: string;
  reason: string;
  created_at: string;
  total_weeks: number;
  goal_summary: string;
}

export type RescheduleOptionType =
  | "REBALANCE"
  | "EXTEND"
  | "REDUCE"
  | "INTENSIFY";

export interface RescheduleOption {
  type: RescheduleOptionType;
  title: string;
  description: string;
  trade_offs: string;
  estimated_new_deadline: string | null;
}

export interface RescheduleAnalysis {
  should_reschedule: boolean;
  reason: string;
  completion_rate: number;
  weeks_behind: number;
  options: RescheduleOption[];
}

export interface RescheduleRequest {
  option_type: RescheduleOptionType;
  additional_params?: Record<string, unknown>;
}

export interface RescheduleResult {
  plan_id: string;
  summary: string;
  changes: string[];
  version: number;
}

export type ProgressStatus = "pending" | "completed" | "skipped" | "rescheduled";

export interface ProgressEntry {
  id: string;
  plan_id: string;
  week_number: number | null;
  day_name: string | null;
  session_index: number;
  status: ProgressStatus;
  actual_duration: number | null;
  difficulty_rating: number | null;
  notes: string | null;
  scheduled_at: string | null;
  completed_at: string | null;
}

export interface ProgressStats {
  completion_rate: number;
  total_sessions: number;
  completed: number;
  skipped: number;
  pending: number;
  total_hours: number;
  current_streak: number;
  longest_streak: number;
}

export interface ProgressMark {
  week_number: number;
  day_name: string;
  session_index: number;
  status: ProgressStatus;
  actual_duration?: number | null;
  difficulty_rating?: number | null;
  notes?: string | null;
}

// Kunci unik sesi — dipakai untuk memetakan progress ke jadwal.
export function progressSessionKey(
  weekNumber: number,
  dayName: string,
  sessionIndex: number
): string {
  return `${weekNumber}:${dayName}:${sessionIndex}`;
}

// --- Axios instance ---
export const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

// Token disimpan di module scope agar interceptor tidak bergantung pada store.
let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

// Request interceptor: inject Authorization Bearer token.
api.interceptors.request.use((config) => {
  const token =
    authToken ??
    (typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401 (clear token + redirect /login).
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// Ambil pesan error yang ramah dari respons backend.
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
    if (error.code === "ERR_NETWORK") return "Cannot reach the server.";
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

// True kalau error karena jaringan/offline (bukan validasi server).
export function isNetworkError(error: unknown): boolean {
  if (axios.isAxiosError(error)) {
    return error.code === "ERR_NETWORK" || error.response === undefined;
  }
  return error instanceof TypeError; // fetch gagal (offline)
}

// Baca SSE dari ReadableStream dan panggil onEvent untuk setiap payload `data:`.
async function consumeSse(
  response: Response,
  onEvent: (payload: string) => void
): Promise<void> {
  if (!response.body) throw new Error("Streaming is not supported.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const dataLines = part
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).replace(/^ /, ""));
      if (dataLines.length === 0) continue;
      const payload = dataLines.join("\n");
      if (payload === "[DONE]") return;
      onEvent(payload);
    }
  }
}

// --- Endpoints ---
export const authApi = {
  signup: async (data: { email: string; password: string; name?: string }) =>
    (await api.post<TokenResponse>("/api/auth/signup", data)).data,
  login: async (data: { email: string; password: string }) =>
    (await api.post<TokenResponse>("/api/auth/login", data)).data,
  me: async () => (await api.get<User>("/api/auth/me")).data,
  verifyOtp: async (email: string, otp: string) =>
    (await api.post<TokenResponse>("/api/auth/verify-otp", { email, otp })).data,
  resendOtp: async (email: string) =>
    (await api.post<{ message: string }>("/api/auth/resend-otp", { email })).data,
};

export const goalsApi = {
  list: async () => (await api.get<Goal[]>("/api/goals")).data,
  create: async (data: GoalCreate) =>
    (await api.post<Goal>("/api/goals", data)).data,
  get: async (id: string) => (await api.get<Goal>(`/api/goals/${id}`)).data,
  update: async (id: string, data: Partial<GoalCreate> & { status?: string }) =>
    (await api.patch<Goal>(`/api/goals/${id}`, data)).data,
  remove: async (id: string) => {
    await api.delete(`/api/goals/${id}`);
  },
};

export const feasibilityApi = {
  check: async (data: FeasibilityRequest) =>
    (await api.post<FeasibilityResponse>("/api/feasibility/check", data)).data,
  rescope: async (goal: FeasibilityRequest, feasibility: FeasibilityResponse) =>
    (
      await api.post<RescopeSuggestion>("/api/feasibility/rescope", {
        goal,
        feasibility,
      })
    ).data,
};

export const plansApi = {
  generate: async (data: {
    goal_id: string;
    feasibility_result?: FeasibilityResponse;
  }) => (await api.post<PlanResponse>("/api/plans/generate", data)).data,
  getById: async (id: string) =>
    (await api.get<PlanResponse>(`/api/plans/${id}`)).data,
  getByGoal: async (goalId: string, version?: number) =>
    (
      await api.get<PlanResponse>(`/api/plans/by-goal/${goalId}`, {
        params: version != null ? { version } : undefined,
      })
    ).data,
  history: async (goalId: string) =>
    (await api.get<PlanVersion[]>(`/api/plans/by-goal/${goalId}/history`)).data,
  // Lazy generation: minta jadwal 4 minggu berikutnya.
  generateNextMonth: async (
    planId: string,
    language: "en" | "id" | "zh" = "en"
  ) =>
    (
      await api.post<PlanResponse>(
        `/api/plans/${planId}/generate-next-month`,
        { language }
      )
    ).data,
  // Streaming generation: status → delta teks → plan final.
  generateStream: async (
    data: {
      goal_id: string;
      feasibility_result?: FeasibilityResponse;
      language?: "en" | "id" | "zh";
    },
    handlers: {
      onStatus?: (stage: string) => void;
      onDelta?: (content: string) => void;
      onPlan?: (plan: PlanResponse) => void;
      onError?: (message: string) => void;
    }
  ): Promise<void> => {
    const token =
      typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null;
    const response = await fetch(`${API_URL}/api/plans/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error(`Plan generation failed (${response.status}).`);
    }
    let failure: string | null = null;
    await consumeSse(response, (payload) => {
      let event: {
        type?: string;
        stage?: string;
        content?: string;
        plan?: PlanResponse;
        message?: string;
      };
      try {
        event = JSON.parse(payload);
      } catch {
        return;
      }
      if (event.type === "status" && event.stage) handlers.onStatus?.(event.stage);
      else if (event.type === "delta" && event.content) handlers.onDelta?.(event.content);
      else if (event.type === "plan" && event.plan) handlers.onPlan?.(event.plan);
      else if (event.type === "error") {
        failure = event.message ?? "Plan generation failed.";
        handlers.onError?.(failure);
      }
    });
    if (failure) throw new Error(failure);
  },
};

export const progressApi = {
  mark: async (planId: string, data: ProgressMark) =>
    (await api.patch<ProgressEntry>(`/api/plans/${planId}/progress`, data)).data,
  list: async (planId: string) =>
    (await api.get<ProgressEntry[]>(`/api/plans/${planId}/progress`)).data,
  stats: async (planId: string) =>
    (await api.get<ProgressStats>(`/api/plans/${planId}/progress/stats`)).data,
  reset: async (planId: string) => {
    await api.post(`/api/plans/${planId}/progress/reset`);
  },
};

export const exportApi = {
  pdf: async (planId: string): Promise<Blob> =>
    (
      await api.get<Blob>(`/api/plans/${planId}/export/pdf`, {
        responseType: "blob",
      })
    ).data,
  ics: async (planId: string): Promise<Blob> =>
    (
      await api.get<Blob>(`/api/plans/${planId}/export/ics`, {
        responseType: "blob",
      })
    ).data,
  // Alias sesuai spesifikasi: /api/plans/:id/export-ics
  icsAlias: async (planId: string): Promise<Blob> =>
    (
      await api.get<Blob>(`/api/plans/${planId}/export-ics`, {
        responseType: "blob",
      })
    ).data,
};

export const rescheduleApi = {
  analyze: async (planId: string) =>
    (await api.get<RescheduleAnalysis>(`/api/plans/${planId}/reschedule/analyze`))
      .data,
  apply: async (planId: string, data: RescheduleRequest) =>
    (
      await api.post<RescheduleResult>(
        `/api/plans/${planId}/reschedule/apply`,
        data
      )
    ).data,
};

export interface RecommendedResource {
  id: string;
  topic: string;
  type: string | null;
  name: string;
  url: string | null;
  level: string | null;
  is_free: boolean;
  description: string | null;
  skills: string[];
  similarity_score: number | null;
}

export const resourcesApi = {
  recommend: async (planId: string, topK = 8) =>
    (
      await api.get<RecommendedResource[]>(
        `/api/plans/${planId}/resources/recommend`,
        { params: { top_k: topK } }
      )
    ).data,
};

export interface ChatAction {
  type: string;
  label: string;
  payload: Record<string, unknown>;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | string;
  content: string;
  created_at: string;
  actions?: ChatAction[] | null;
}

export interface ChatActionResult {
  type: string;
  message: string;
  data: Record<string, unknown>;
}

interface ChatStreamHandlers {
  onDelta: (content: string) => void;
  onMessage: (message: ChatMessage) => void;
}

export const chatApi = {
  history: async (goalId: string) =>
    (
      await api.get<{ messages: ChatMessage[] }>(`/api/goals/${goalId}/chat`)
    ).data.messages,
  clear: async (goalId: string) => {
    await api.delete(`/api/goals/${goalId}/chat`);
  },
  executeAction: async (
    goalId: string,
    actionType: string,
    payload: Record<string, unknown>
  ) =>
    (
      await api.post<ChatActionResult>(`/api/goals/${goalId}/chat/action`, {
        action_type: actionType,
        payload,
      })
    ).data,
  // Kirim pesan dan baca respons SSE via fetch (butuh header Authorization).
  stream: async (
    goalId: string,
    message: string,
    handlers: ChatStreamHandlers
  ): Promise<void> => {
    const token =
      typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null;
    const res = await fetch(`${API_URL}/api/goals/${goalId}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message }),
    });
    if (!res.ok || !res.body) {
      throw new Error(`Chat request failed (${res.status}).`);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      for (const part of parts) {
        const line = part
          .split("\n")
          .find((item) => item.startsWith("data: "));
        if (!line) continue;
        const payload = line.slice(6);
        if (payload === "[DONE]") return;
        const event = JSON.parse(payload) as {
          type: string;
          content?: string;
          message?: ChatMessage;
        };
        if (event.type === "delta" && event.content) {
          handlers.onDelta(event.content);
        } else if (event.type === "message" && event.message) {
          handlers.onMessage(event.message);
        }
      }
    }
  },
};

export interface TutorMessage {
  role: "user" | "assistant";
  content: string;
}

export interface QuizQuestion {
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
}

export interface QuizResponse {
  topic: string;
  questions: QuizQuestion[];
}

export const tutorApi = {
  // Tanya tutor (streaming SSE, reasoning low).
  stream: async (
    payload: {
      topic: string;
      question: string;
      history?: TutorMessage[];
      language?: string;
    },
    handlers: { onDelta: (content: string) => void; onDone?: () => void }
  ): Promise<void> => {
    const response = await fetch(`${API_URL}/api/tutor/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(`Tutor request failed (${response.status}).`);
    }
    await consumeSse(response, (frame) => {
      let event: { type?: string; content?: string };
      try {
        event = JSON.parse(frame);
      } catch {
        return;
      }
      if (event.type === "delta" && event.content) {
        handlers.onDelta(event.content);
      }
    });
    handlers.onDone?.();
  },
  // Quiz dari jadwal (JSON, butuh auth).
  quiz: async (planId: string, weekNumber: number, dayName: string) =>
    (
      await api.post<QuizResponse>("/api/tutor/chat", {
        mode: "quiz_from_schedule",
        plan_id: planId,
        week_number: weekNumber,
        day_name: dayName,
      })
    ).data,
};

export interface QuizAttempt {
  id: string;
  plan_id: string;
  week_number: number;
  day_name: string;
  score: number;
  total_questions: number;
  created_at: string;
  goal_topic: string | null;
}

export interface QuizHistory {
  attempts: QuizAttempt[];
  total_quizzes: number;
  average_score: number;
  best_score: number;
}

export const quizApi = {
  // Simpan hasil quiz setelah user selesai menjawab.
  submit: async (data: {
    plan_id: string;
    week_number: number;
    day_name: string;
    score: number;
    total_questions: number;
  }) => (await api.post<QuizAttempt>("/api/quizzes/submit", data)).data,
  // Riwayat + statistik quiz user.
  history: async () => (await api.get<QuizHistory>("/api/quizzes/history")).data,
};
