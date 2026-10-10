# Skema Pydantic untuk fitur F-02: Goal Feasibility Check.

from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Nilai verdict yang diizinkan.
Verdict = Literal["REALISTIC", "REALISTIC_WITH_NOTES", "UNREALISTIC"]


class FeasibilityRequest(BaseModel):
    # Input dari user untuk dianalisis kelayakannya.
    topic: str = Field(min_length=1, max_length=200)
    current_level: str = Field(min_length=1, max_length=100)
    target: str = Field(min_length=1, max_length=300)
    deadline_months: int = Field(gt=0, le=120)
    # Format "HH:MM", mis. "09:00".
    work_hours_start: str = Field(pattern=r"^\d{2}:\d{2}$")
    work_hours_end: str = Field(pattern=r"^\d{2}:\d{2}$")
    work_days: list[str] = Field(min_length=1)
    preferred_study_time: str = Field(min_length=1, max_length=50)
    max_session_minutes: int = Field(gt=0, le=600)
    # Hari yang tidak bisa dipakai belajar (mis. libur/keluarga).
    unavailable_days: list[str] = Field(default_factory=list)

    @field_validator("work_hours_start", "work_hours_end")
    @classmethod
    def validate_time_range(cls, value: str) -> str:
        # Cek jam 00-23 dan menit 00-59.
        hours, minutes = (int(part) for part in value.split(":"))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError(f"Invalid time value: {value}")
        return value


class FeasibilityResponse(BaseModel):
    # Hasil analisis kelayakan. Semua teks dalam Bahasa Inggris.
    feasible: bool
    confidence: float = Field(ge=0.0, le=1.0)
    required_hours: int = Field(ge=0)
    available_hours: int = Field(ge=0)
    gap_hours: int
    verdict: Verdict
    analysis: str
    recommendations: list[str]
    benchmark_source: str | None = None
    # True kalau confidence < 0.6 (sesuai guardrail PRD: manual review).
    requires_manual_review: bool = False

    @field_validator("verdict", mode="before")
    @classmethod
    def normalize_verdict(cls, value: str) -> str:
        # Terima variasi dari LLM: "realistic", "Realistic With Notes", dll.
        return str(value).strip().upper().replace("-", "_").replace(" ", "_")

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, value: float) -> float:
        # Jaga nilai confidence tetap di rentang 0..1.
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, number))
