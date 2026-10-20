# Skema Pydantic untuk fitur Socratic Tutor + Quiz dari jadwal.

import uuid
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TutorMessage(BaseModel):
    # Satu pesan riwayat percakapan dengan tutor.
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class TutorRequest(BaseModel):
    # Input untuk bertanya ke tutor (mode "chat") atau minta quiz (mode "quiz_from_schedule").
    topic: str = Field(default="General", max_length=200)
    question: str = Field(default="", max_length=2000)
    history: list[TutorMessage] = Field(default_factory=list)
    language: str | None = Field(default=None, max_length=20)
    mode: Literal["chat", "quiz_from_schedule"] = "chat"
    # Dipakai untuk mode quiz_from_schedule.
    plan_id: uuid.UUID | None = None
    week_number: int | None = Field(default=None, ge=1)
    day_name: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def validate_mode(self) -> "TutorRequest":
        if self.mode == "chat" and not self.question.strip():
            raise ValueError("question is required for chat mode.")
        if self.mode == "quiz_from_schedule":
            if self.plan_id is None or self.week_number is None or not self.day_name:
                raise ValueError(
                    "plan_id, week_number and day_name are required for quiz mode."
                )
        return self


class QuizQuestion(BaseModel):
    # Satu soal pilihan ganda.
    question: str
    options: list[str] = Field(min_length=2)
    correct_index: int = Field(ge=0)
    explanation: str


class QuizResponse(BaseModel):
    # 3 soal quiz berdasarkan topik sesi pada jadwal.
    topic: str
    questions: list[QuizQuestion]
