# Skema Pydantic untuk fitur F-04: Progress Tracker.

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Status sesi yang diizinkan.
ProgressStatus = Literal["pending", "completed", "skipped", "rescheduled"]


class ProgressUpdate(BaseModel):
    # Data yang bisa diubah pada satu sesi.
    status: ProgressStatus
    actual_duration: int | None = Field(default=None, ge=0, le=1440)
    difficulty_rating: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = Field(default=None, max_length=2000)
    scheduled_at: datetime | None = None


class ProgressMark(ProgressUpdate):
    # Body PATCH: identitas sesi + data update.
    week_number: int = Field(ge=1)
    day_name: str = Field(min_length=1, max_length=20)
    session_index: int = Field(default=0, ge=0)


class ProgressEntry(BaseModel):
    # Representasi entry progres yang dikembalikan ke client.
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan_id: uuid.UUID
    week_number: int | None = None
    day_name: str | None = None
    session_index: int
    status: ProgressStatus
    actual_duration: int | None = None
    difficulty_rating: int | None = None
    notes: str | None = None
    scheduled_at: datetime | None = None
    completed_at: datetime | None = None


class ProgressStats(BaseModel):
    # Ringkasan progres untuk dashboard.
    completion_rate: float
    total_sessions: int
    completed: int
    skipped: int
    pending: int
    total_hours: float
    current_streak: int
    longest_streak: int
