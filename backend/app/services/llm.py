# LLM service wrapper — DeepSeek V4.1 Flash via OpenAI SDK (async).

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from functools import lru_cache
from typing import Any, TypeVar

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.schemas.llm import LLMResponse, TokenUsage

logger = logging.getLogger(__name__)

# --- Retry config ---
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1.0

T = TypeVar("T")


class LLMTruncatedError(RuntimeError):
    # Output LLM terpotong karena max_tokens (finish_reason="length").
    # Dipakai caller untuk memberi pesan actionable.
    pass


@lru_cache(maxsize=1)
def get_client() -> AsyncOpenAI:
    # Async client DeepSeek (kompatibel OpenAI). API key tidak pernah di-hardcode.
    if not settings.deepseek_api_key or settings.deepseek_api_key.startswith("your-"):
        raise RuntimeError(
            "DEEPSEEK_API_KEY belum di-set. Isi dulu di backend/.env"
        )
    return AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        timeout=60.0,
        max_retries=0,  # retry kita tangani sendiri
    )


def _is_retryable(exc: Exception) -> bool:
    # Rate limit (429) dan server error (5xx) boleh di-retry.
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APIStatusError) and exc.status_code >= 500:
        return True
    # Masalah koneksi/timeout juga layak dicoba ulang.
    if isinstance(exc, (APITimeoutError, APIConnectionError)):
        return True
    return False


async def _with_retry(factory: Callable[[], Awaitable[T]], *, label: str) -> T:
    # Jalankan `factory` dengan exponential backoff untuk error yang retryable.
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await factory()
        except Exception as exc:  # noqa: BLE001 - sengaja menangkap semua untuk klasifikasi
            last_exc = exc
            if not _is_retryable(exc) or attempt == MAX_RETRIES:
                raise
            delay = BASE_DELAY_SECONDS * (2 ** (attempt - 1))
            logger.warning(
                "[%s] gagal (attempt %d/%d): %s — retry dalam %.1fs",
                label,
                attempt,
                MAX_RETRIES,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
    # Tidak akan tercapai, tapi jaga-jaga.
    raise last_exc  # type: ignore[misc]


def _build_messages(prompt: str, system: str | None) -> list[dict[str, str]]:
    # Susun messages; taruh system (static) di depan agar context caching optimal.
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return messages


def _build_extra_body(thinking: bool | None) -> dict[str, Any] | None:
    # `thinking` bukan param standar OpenAI → kirim via extra_body.
    if thinking is None:
        return None
    return {"thinking": {"type": "enabled" if thinking else "disabled"}}


def _build_request_kwargs(
    *,
    temperature: float,
    max_tokens: int,
    reasoning_effort: str | None,
    thinking: bool | None,
    extra_body: dict[str, Any] | None,
    json_mode: bool,
) -> dict[str, Any]:
    # Kumpulkan parameter opsional yang benar-benar di-set oleh caller.
    kwargs: dict[str, Any] = {
        "model": settings.deepseek_model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if reasoning_effort is not None:
        kwargs["reasoning_effort"] = reasoning_effort
    merged_extra = {**(extra_body or {}), **(_build_extra_body(thinking) or {})}
    if merged_extra:
        kwargs["extra_body"] = merged_extra
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    return kwargs


def _parse_usage(usage: Any) -> TokenUsage:
    # Konversi usage OpenAI → TokenUsage Pydantic.
    if usage is None:
        return TokenUsage()
    return TokenUsage(
        prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
        completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
        total_tokens=getattr(usage, "total_tokens", 0) or 0,
    )


async def chat_completion(
    prompt: str,
    system: str | None = None,
    *,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    reasoning_effort: str | None = None,
    thinking: bool | None = None,
    extra_body: dict[str, Any] | None = None,
    **kwargs: Any,
) -> LLMResponse:
    # Mode basic: single completion non-streaming.
    client = get_client()
    request_kwargs = _build_request_kwargs(
        temperature=temperature,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
        thinking=thinking,
        extra_body=extra_body,
        json_mode=False,
    )
    request_kwargs.update(kwargs)  # override tambahan dari caller
    request_kwargs["messages"] = _build_messages(prompt, system)

    logger.info(
        "LLM request [basic] model=%s prompt_chars=%d temperature=%s max_tokens=%s reasoning_effort=%s thinking=%s",
        settings.deepseek_model,
        len(prompt),
        temperature,
        max_tokens,
        reasoning_effort,
        thinking,
    )

    started = time.perf_counter()
    response = await _with_retry(
        lambda: client.chat.completions.create(**request_kwargs), label="basic"
    )
    latency_ms = (time.perf_counter() - started) * 1000

    content = response.choices[0].message.content or ""
    finish_reason = response.choices[0].finish_reason
    usage = _parse_usage(response.usage)
    logger.info(
        "LLM response [basic] model=%s latency_ms=%.0f finish_reason=%s tokens=%s",
        response.model,
        latency_ms,
        finish_reason,
        usage.model_dump(),
    )

    return LLMResponse(
        content=content,
        usage=usage,
        model=response.model,
        latency_ms=round(latency_ms, 2),
        finish_reason=finish_reason,
    )


async def chat_completion_json(
    prompt: str,
    system: str | None = None,
    schema: type[BaseModel] | None = None,
    *,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    reasoning_effort: str | None = None,
    thinking: bool | None = None,
    extra_body: dict[str, Any] | None = None,
    **kwargs: Any,
) -> LLMResponse:
    # Mode JSON: paksa output JSON object, validasi opsional ke `schema`.
    client = get_client()
    request_kwargs = _build_request_kwargs(
        temperature=temperature,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
        thinking=thinking,
        extra_body=extra_body,
        json_mode=True,
    )
    request_kwargs.update(kwargs)
    request_kwargs["messages"] = _build_messages(prompt, system)

    logger.info(
        "LLM request [json] model=%s prompt_chars=%d schema=%s",
        settings.deepseek_model,
        len(prompt),
        schema.__name__ if schema else None,
    )

    started = time.perf_counter()
    response = await _with_retry(
        lambda: client.chat.completions.create(**request_kwargs), label="json"
    )
    latency_ms = (time.perf_counter() - started) * 1000

    content = response.choices[0].message.content or ""
    finish_reason = response.choices[0].finish_reason
    usage = _parse_usage(response.usage)

    if finish_reason == "length":
        logger.warning(
            "LLM [json] output TRUNCATED (finish_reason=length, max_tokens=%s). "
            "JSON kemungkinan tidak lengkap.",
            max_tokens,
        )

    # Parse + validasi. Kalau gagal, log lalu naikkan error (bukan retry otomatis).
    data: dict[str, Any] | None = None
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        if finish_reason == "length":
            logger.error("LLM [json] output terpotong; JSON tidak lengkap: %s", exc)
            raise LLMTruncatedError(
                "LLM output was truncated (finish_reason=length) and produced incomplete JSON."
            ) from exc
        logger.error("LLM [json] mengembalikan JSON tidak valid: %s", exc)
        raise ValueError(f"LLM tidak mengembalikan JSON valid: {exc}") from exc

    if schema is not None:
        try:
            schema.model_validate(data)
        except ValidationError as exc:
            logger.error("LLM [json] output tidak sesuai schema %s: %s", schema.__name__, exc)
            raise

    logger.info(
        "LLM response [json] model=%s latency_ms=%.0f finish_reason=%s tokens=%s",
        response.model,
        latency_ms,
        finish_reason,
        usage.model_dump(),
    )

    return LLMResponse(
        content=content,
        usage=usage,
        model=response.model,
        latency_ms=round(latency_ms, 2),
        finish_reason=finish_reason,
        data=data,
    )


async def chat_completion_stream(
    prompt: str,
    system: str | None = None,
    *,
    temperature: float = 0.7,
    max_tokens: int = 8192,
    reasoning_effort: str | None = None,
    thinking: bool | None = None,
    extra_body: dict[str, Any] | None = None,
    **kwargs: Any,
) -> AsyncIterator[str]:
    # Mode streaming: yield potongan teks (delta content) saat diterima.
    client = get_client()
    request_kwargs = _build_request_kwargs(
        temperature=temperature,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
        thinking=thinking,
        extra_body=extra_body,
        json_mode=False,
    )
    request_kwargs.update(kwargs)
    request_kwargs["messages"] = _build_messages(prompt, system)
    request_kwargs["stream"] = True

    logger.info(
        "LLM request [stream] model=%s prompt_chars=%d",
        settings.deepseek_model,
        len(prompt),
    )

    started = time.perf_counter()
    # Retry hanya untuk pembentukan stream (sebelum token pertama).
    stream = await _with_retry(
        lambda: client.chat.completions.create(**request_kwargs), label="stream"
    )

    chunks = 0
    try:
        async for event in stream:
            delta = event.choices[0].delta.content if event.choices else None
            if delta:
                chunks += 1
                yield delta
    finally:
        # Tutup stream walau consumer berhenti lebih awal.
        await stream.close()
        latency_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "LLM response [stream] selesai latency_ms=%.0f chunks=%d",
            latency_ms,
            chunks,
        )
