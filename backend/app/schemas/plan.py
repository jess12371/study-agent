# Skema Pydantic untuk fitur F-03: Study Plan Generator.

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.feasibility import FeasibilityRequest, FeasibilityResponse


class Resource(BaseModel):
    # Referensi materi belajar. Semua teks dalam Bahasa Inggris.
    # extra="allow" agar field tambahan dari LLM tidak membuat validasi gagal.
    model_config = ConfigDict(extra="allow")

    type: str  # book / app / video / website / tool
    name: str
    url: str | None = None
    for_skill: str | None = None


class Milestone(BaseModel):
    # Target capaian per bulan.
    model_config = ConfigDict(extra="allow")

    month: int = Field(ge=1)
    focus: str
    target: str
    checkpoint: str


class DaySession(BaseModel):
    # Satu sesi belajar pada hari tertentu.
    model_config = ConfigDict(extra="allow")

    day: str
    # Jarak hari dari mulai plan (0 = hari pertama).
    date_offset: int = 0
    time: str = ""
    topic: str
    duration_minutes: int = Field(ge=0)
    activities: list[str] = Field(default_factory=list)
    resources: list[Resource] = Field(default_factory=list)


class WeekSchedule(BaseModel):
    # Jadwal satu minggu.
    model_config = ConfigDict(extra="allow")

    week: int = Field(ge=1)
    theme: str
    days: list[DaySession] = Field(default_factory=list)


class PlanRequest(BaseModel):
    # Input internal untuk generate plan (dibangun server dari goal di DB).
    goal: FeasibilityRequest
    feasibility_result: FeasibilityResponse


class PlanGenerateRequest(BaseModel):
    # Body request endpoint generate plan. Goal diambil dari DB berdasarkan goal_id.
    goal_id: uuid.UUID
    # Opsional: kalau tidak dikirim, server menjalankan feasibility check sendiri.
    feasibility_result: FeasibilityResponse | None = None


class PlanResponse(BaseModel):
    # Hasil study plan. Semua teks dalam Bahasa Inggris.
    plan_id: uuid.UUID
    goal_summary: str
    total_weeks: int
    milestones: list[Milestone]
    weekly_schedule: list[WeekSchedule]
    resources: list[Resource]
    created_at: datetime
    # Versi plan (naik setelah reschedule / regenerate).
    version: int = 1
    # Status: active / superseded.
    status: str = "active"
    # Alasan versi ini: initial / reschedule / regenerate.
    reason: str = "initial"


class PlanVersion(BaseModel):
    # Ringkasan satu versi plan untuk Plan History.
    plan_id: uuid.UUID
    version: int
    status: str
    reason: str
    created_at: datetime
    total_weeks: int
    goal_summary: str
