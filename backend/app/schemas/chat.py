# Skema Pydantic untuk fitur F-11: Agent Dialog (chat).

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatAction(BaseModel):
    # Tombol aksi yang ditawarkan agent.
    type: str
    label: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    # Satu pesan dalam riwayat dialog.
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str  # user / assistant
    content: str
    created_at: datetime
    actions: list[ChatAction] | None = None


class ChatRequest(BaseModel):
    # Body untuk mengirim pesan.
    message: str = Field(min_length=1, max_length=2000)
    goal_id: uuid.UUID | None = None


class ChatResponse(BaseModel):
    # Respons agent (teks + action buttons).
    message: ChatMessage
    actions: list[ChatAction] = Field(default_factory=list)


class ChatHistoryResponse(BaseModel):
    # Riwayat dialog sebuah goal.
    messages: list[ChatMessage]


class ChatActionRequest(BaseModel):
    # Body untuk mengeksekusi action button.
    action_type: str = Field(min_length=1, max_length=50)
    payload: dict[str, Any] = Field(default_factory=dict)


class ChatActionResult(BaseModel):
    # Hasil eksekusi action button.
    type: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
