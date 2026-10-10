# Skema Pydantic untuk request/response LLM.

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TokenUsage(BaseModel):
    # Pemakaian token dari response LLM.
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMRequest(BaseModel):
    # Parameter pemanggilan LLM (opsional, dipakai kalau mau sentralisasi).
    prompt: str
    system: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    # "low" | "medium" | "high" — sesuai konfigurasi per task di PRD section 9.
    reasoning_effort: str | None = None
    # True = thinking enabled, False = disabled, None = pakai default API.
    thinking: bool | None = None
    json_mode: bool = False


class LLMResponse(BaseModel):
    # Hasil pemanggilan LLM.
    # protected_namespaces dinonaktifkan agar field `model` tidak memicu warning.
    model_config = ConfigDict(protected_namespaces=())

    content: str
    usage: TokenUsage = Field(default_factory=TokenUsage)
    model: str
    latency_ms: float
    # Alasan berhentinya LLM: "stop", "length" (terpotong), dll.
    finish_reason: str | None = None
    # Diisi hanya untuk mode JSON: hasil parsing content (None kalau bukan JSON mode).
    data: dict[str, Any] | None = None
