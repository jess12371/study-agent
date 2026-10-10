# Skema Pydantic untuk goals (F-01).

import uuid
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Format jam "HH:MM".
TIME_PATTERN = r"^\d{2}:\d{2}$"


def _validate_hhmm(value: str) -> str:
    hours, minutes = (int(part) for part in value.split(":"))
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        raise ValueError(f"Invalid time value: {value}")
    return value


def _format_time(value: time | str | None) -> str | None:
    # Serialize datetime.time → "HH:MM".
    if value is None:
        return None
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return value


class GoalCreate(BaseModel):
    # Payload buat goal.
    topic: str = Field(min_length=1, max_length=200)
    current_level: str = Field(min_length=1, max_length=100)
    target: str = Field(min_length=1, max_length=300)
    deadline_months: int = Field(gt=0, le=120)
    work_hours_start: str = Field(pattern=TIME_PATTERN)
    work_hours_end: str = Field(pattern=TIME_PATTERN)
    work_days: list[str] = Field(min_length=1)
    preferred_study_time: str = Field(min_length=1, max_length=50)
    max_session_minutes: int = Field(gt=0, le=600)
    unavailable_days: list[str] = Field(default_factory=list)

    @field_validator("work_hours_start", "work_hours_end")
    @classmethod
    def validate_time(cls, value: str) -> str:
        return _validate_hhmm(value)


class GoalUpdate(BaseModel):
    # Semua field opsional untuk PATCH.
    topic: str | None = Field(default=None, min_length=1, max_length=200)
    current_level: str | None = Field(default=None, min_length=1, max_length=100)
    target: str | None = Field(default=None, min_length=1, max_length=300)
    deadline_months: int | None = Field(default=None, gt=0, le=120)
    work_hours_start: str | None = Field(default=None, pattern=TIME_PATTERN)
    work_hours_end: str | None = Field(default=None, pattern=TIME_PATTERN)
    work_days: list[str] | None = None
    preferred_study_time: str | None = Field(default=None, min_length=1, max_length=50)
    max_session_minutes: int | None = Field(default=None, gt=0, le=600)
    unavailable_days: list[str] | None = None
    status: str | None = Field(default=None, max_length=20)

    @field_validator("work_hours_start", "work_hours_end")
    @classmethod
    def validate_time(cls, value: str | None) -> str | None:
        return None if value is None else _validate_hhmm(value)


class GoalResponse(BaseModel):
    # Data goal yang dikembalikan ke client.
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    topic: str
    current_level: str | None = None
    target: str | None = None
    deadline_months: int | None = None
    work_hours_start: str | None = None
    work_hours_end: str | None = None
    work_days: list[str] | None = None
    preferred_study_time: str | None = None
    max_session_minutes: int | None = None
    unavailable_days: list[str] | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    @field_validator("work_hours_start", "work_hours_end", mode="before")
    @classmethod
    def serialize_time(cls, value: time | str | None) -> str | None:
        return _format_time(value)
