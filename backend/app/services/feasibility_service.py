# Service F-02 — Goal Feasibility Check.
# Menganalisis apakah target belajar realistis dengan waktu yang tersedia,
# memakai LLM (DeepSeek) dengan reasoning_effort="high" + thinking enabled.

import logging
from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import settings
from app.schemas.feasibility import FeasibilityRequest, FeasibilityResponse
from app.schemas.llm import LLMResponse
from app.services import llm

logger = logging.getLogger(__name__)

# Batas token output feasibility check (bisa dioverride via FEASIBILITY_MAX_TOKENS).
FEASIBILITY_MAX_TOKENS = settings.feasibility_max_tokens

# Rata-rata jumlah minggu per bulan.
WEEKS_PER_MONTH = 4.345

SYSTEM_PROMPT = """You are Study Agent, an expert learning plan feasibility analyzer.

Your task: analyze if a learning goal is realistic given the user's available time and deadline.

RULES:
1. Cite benchmark sources when estimating required hours
2. If target unrealistic, provide 2-3 alternatives
3. Output MUST be valid JSON matching the schema
4. All text in English
5. Be supportive but realistic — don't over-promise

TONE: Supportive, realistic, motivating
"""

USER_PROMPT_TEMPLATE = """Analyze the feasibility of this learning goal.

GOAL DETAILS:
- Topic: {topic}
- Current level: {current_level}
- Target: {target}
- Deadline: {deadline_months} months
- Work hours: {work_hours_start}-{work_hours_end}
- Work days: {work_days}
- Preferred study time: {preferred_study_time}
- Max session length: {max_session_minutes} minutes
- Unavailable days (cannot study): {unavailable_days}

PRECOMPUTED AVAILABLE STUDY HOURS: {available_hours} hours.
(Use exactly this integer for the "available_hours" field.)

INSTRUCTIONS:
- Estimate the required hours to reach the target from the current level.
- Compare required hours against the available hours.
- Set "verdict" to exactly one of: REALISTIC, REALISTIC_WITH_NOTES, UNREALISTIC.
- Set "feasible" to true only when verdict is REALISTIC or REALISTIC_WITH_NOTES.
- If the target is unrealistic, put 2-3 concrete alternatives (adjusted target or timeline) in "recommendations".
- Put a known benchmark/source for the hour estimate in "benchmark_source"; if you have none, use "estimate".
- Respond in English.

Respond ONLY with a JSON object with exactly these keys:
{{
  "feasible": true,
  "confidence": 0.0,
  "required_hours": 0,
  "available_hours": 0,
  "gap_hours": 0,
  "verdict": "REALISTIC",
  "analysis": "string",
  "recommendations": ["string"],
  "benchmark_source": "string or null"
}}
"""


class _LLMFeasibilityOutput(BaseModel):
    # Bentuk JSON yang diminta dari LLM (dipakai untuk validasi output).
    feasible: bool
    confidence: float
    required_hours: int
    available_hours: int
    gap_hours: int
    verdict: Literal["REALISTIC", "REALISTIC_WITH_NOTES", "UNREALISTIC"]
    analysis: str
    recommendations: list[str] = Field(default_factory=list)
    benchmark_source: str | None = None


def compute_available_hours(request: FeasibilityRequest) -> int:
    # Hitung kapasitas belajar: hari tersedia/minggu x durasi sesi x jumlah minggu.
    unavailable = {day.strip().lower() for day in request.unavailable_days if day.strip()}
    available_days_per_week = max(0, 7 - len(unavailable))
    weekly_hours = available_days_per_week * (request.max_session_minutes / 60)
    total_weeks = request.deadline_months * WEEKS_PER_MONTH
    return round(weekly_hours * total_weeks)


def _build_user_prompt(request: FeasibilityRequest, available_hours: int) -> str:
    return USER_PROMPT_TEMPLATE.format(
        topic=request.topic,
        current_level=request.current_level,
        target=request.target,
        deadline_months=request.deadline_months,
        work_hours_start=request.work_hours_start,
        work_hours_end=request.work_hours_end,
        work_days=", ".join(request.work_days),
        preferred_study_time=request.preferred_study_time,
        max_session_minutes=request.max_session_minutes,
        unavailable_days=", ".join(request.unavailable_days) or "none",
        available_hours=available_hours,
    )


async def _call_llm(request: FeasibilityRequest, available_hours: int) -> LLMResponse:
    # Panggil LLM dengan penanganan khusus untuk output yang terpotong.
    try:
        llm_response = await llm.chat_completion_json(
            _build_user_prompt(request, available_hours),
            system=SYSTEM_PROMPT,
            schema=_LLMFeasibilityOutput,
            temperature=0.7,
            max_tokens=FEASIBILITY_MAX_TOKENS,
            reasoning_effort="high",
            thinking=True,
        )
    except llm.LLMTruncatedError as exc:
        # JSON tidak lengkap karena kehabisan token.
        logger.warning(
            "Feasibility output truncated (finish_reason=length, max_tokens=%d) untuk target=%r",
            FEASIBILITY_MAX_TOKENS,
            request.target,
        )
        raise ValueError(
            "Feasibility output truncated. Increase max_tokens or simplify prompt."
        ) from exc

    if llm_response.finish_reason == "length":
        # JSON sempat ter-parse tapi tetap ditandai terpotong → tetap tolak.
        logger.warning(
            "Feasibility output truncated (finish_reason=length, max_tokens=%d) untuk target=%r",
            FEASIBILITY_MAX_TOKENS,
            request.target,
        )
        raise ValueError(
            "Feasibility output truncated. Increase max_tokens or simplify prompt."
        )

    return llm_response


async def check_feasibility_with_meta(
    request: FeasibilityRequest,
) -> tuple[FeasibilityResponse, LLMResponse]:
    # Versi internal: kembalikan response + metadata LLM (latency, token usage).
    available_hours = compute_available_hours(request)

    logger.info(
        "Feasibility check: topic=%r target=%r deadline_months=%d available_hours=%d",
        request.topic,
        request.target,
        request.deadline_months,
        available_hours,
    )

    llm_response = await _call_llm(request, available_hours)

    output = _LLMFeasibilityOutput.model_validate(llm_response.data)

    # available_hours & gap_hours dihitung ulang agar konsisten (deterministik).
    required_hours = max(0, output.required_hours)
    gap_hours = required_hours - available_hours

    recommendations = [rec.strip() for rec in output.recommendations if rec.strip()]

    # Guardrail: target tidak realistis WAJIB punya minimal 2 alternatif.
    if not output.feasible and len(recommendations) < 2:
        raise ValueError(
            "LLM returned an infeasible verdict with fewer than 2 recommendations; "
            "cannot satisfy the 'provide alternatives' guardrail."
        )

    # Guardrail: benchmark kosong -> tandai "estimate".
    benchmark_source = (output.benchmark_source or "").strip() or "estimate"

    # Guardrail: confidence < 0.6 -> flag manual review.
    requires_manual_review = output.confidence < 0.6
    if requires_manual_review:
        logger.warning(
            "Feasibility confidence rendah (%.2f) untuk target=%r — flag manual review",
            output.confidence,
            request.target,
        )

    response = FeasibilityResponse(
        feasible=output.feasible,
        confidence=output.confidence,
        required_hours=required_hours,
        available_hours=available_hours,
        gap_hours=gap_hours,
        verdict=output.verdict,
        analysis=output.analysis,
        recommendations=recommendations,
        benchmark_source=benchmark_source,
        requires_manual_review=requires_manual_review,
    )

    logger.info(
        "Feasibility result: verdict=%s feasible=%s required_hours=%d available_hours=%d gap_hours=%d",
        response.verdict,
        response.feasible,
        response.required_hours,
        response.available_hours,
        response.gap_hours,
    )

    return response, llm_response


async def check_feasibility(request: FeasibilityRequest) -> FeasibilityResponse:
    # API publik: hanya kembalikan FeasibilityResponse.
    response, _ = await check_feasibility_with_meta(request)
    return response
