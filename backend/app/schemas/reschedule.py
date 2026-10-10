# Skema Pydantic untuk fitur F-05: Adaptive Reschedule.

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# Empat strategi reschedule yang diizinkan.
OptionType = Literal["REBALANCE", "EXTEND", "REDUCE", "INTENSIFY"]


class RescheduleOption(BaseModel):
    # Satu opsi adaptasi yang bisa dipilih user.
    type: OptionType
    title: str
    description: str
    trade_offs: str
    estimated_new_deadline: str | None = None

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value: str) -> str:
        return str(value).strip().upper().replace("-", "_").replace(" ", "_")


class RescheduleAnalysis(BaseModel):
    # Hasil analisis progres + opsi adaptasi.
    should_reschedule: bool
    reason: str
    completion_rate: float
    weeks_behind: int
    options: list[RescheduleOption]


class RescheduleRequest(BaseModel):
    # Pilihan user untuk menerapkan adaptasi.
    option_type: OptionType
    additional_params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("option_type", mode="before")
    @classmethod
    def normalize_type(cls, value: str) -> str:
        return str(value).strip().upper().replace("-", "_").replace(" ", "_")


class RescheduleResult(BaseModel):
    # Hasil penerapan reschedule (plan baru).
    plan_id: uuid.UUID
    summary: str
    changes: list[str]
    version: int = 1
