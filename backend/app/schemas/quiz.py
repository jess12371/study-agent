# Skema Pydantic untuk gamifikasi quiz (riwayat & skor).

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class QuizSubmitRequest(BaseModel):
    # Hasil quiz yang dikirim frontend setelah user selesai menjawab.
    plan_id: uuid.UUID
    week_number: int = Field(ge=1)
    day_name: str = Field(min_length=1, max_length=20)
    score: int = Field(ge=0)
    total_questions: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_score(self) -> "QuizSubmitRequest":
        if self.score > self.total_questions:
            raise ValueError("score cannot exceed total_questions.")
        return self


class QuizAttemptResponse(BaseModel):
    # Satu percobaan quiz.
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan_id: uuid.UUID
    week_number: int
    day_name: str
    score: int
    total_questions: int
    created_at: datetime
    goal_topic: str | None = None

    @property
    def percentage(self) -> float:
        # Persentase skor (0-100).
        if not self.total_questions:
            return 0.0
        return round(self.score / self.total_questions * 100, 1)


class QuizHistoryResponse(BaseModel):
    # Riwayat + agregat statistik quiz user.
    attempts: list[QuizAttemptResponse]
    total_quizzes: int
    average_score: float
    best_score: float
