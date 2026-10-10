# Service F-03 — Study Plan Generator.
# Membuat study plan (milestones + jadwal mingguan + resources) memakai LLM,
# lalu menyimpannya ke tabel `study_plans` (kolom plan_data JSONB).

import logging
import uuid
from collections.abc import AsyncIterator
from datetime import datetime

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.goal import Goal
from app.models.study_plan import StudyPlan
from app.schemas.feasibility import FeasibilityRequest
from app.schemas.plan import (
    Milestone,
    PlanRequest,
    PlanResponse,
    PlanVersion,
    Resource,
    WeekSchedule,
)
from app.services import llm

logger = logging.getLogger(__name__)

# Batas detail jadwal ke N minggu pertama agar output tidak melebihi max_tokens.
DETAILED_WEEKS = settings.plan_detailed_weeks

# max_tokens plan generation (config-driven agar bisa di-tune via .env).
PLAN_MAX_TOKENS = settings.plan_max_tokens

# reasoning_effort plan generation (medium sudah cukup untuk output pola).
PLAN_REASONING_EFFORT = settings.plan_reasoning_effort

SYSTEM_PROMPT = """You are Study Agent, an expert learning plan designer. Always respond in English."""

# --- Context caching: bagian STATIC ditaruh di system message (prefix stabil),
# bagian VARIABLE (goal + feasibility) ditaruh di user message. ---
INSTRUCTIONS_TEMPLATE = """INSTRUCTIONS:
1. Break the target down into monthly milestones (4 weeks per month).
2. Provide a detailed day-by-day weekly schedule for the FIRST __DETAILED_WEEKS__ WEEKS only,
   then focus on monthly themes for the remaining weeks.
3. Allocate sessions OUTSIDE the user's working hours and on available days only.
4. Include specific, mostly free resources per topic.
5. Breakdown target into monthly milestones.
6. Create weekly schedule respecting work hours.
7. Keep every text field CONCISE: goal_summary and checkpoint under 25 words,
   activities 2-3 short bullets per session, and at most 1-2 resources per session.
8. Do not add extra top-level keys. All text in English. Respond ONLY with a JSON object.

Respond ONLY with a JSON object matching exactly this structure:
{
  "goal_summary": "string",
  "total_weeks": 0,
  "milestones": [
    {"month": 1, "focus": "string", "target": "string", "checkpoint": "string"}
  ],
  "weekly_schedule": [
    {
      "week": 1,
      "theme": "string",
      "days": [
        {
          "day": "Monday",
          "date_offset": 0,
          "time": "19:00",
          "topic": "string",
          "duration_minutes": 60,
          "activities": ["string"],
          "resources": [{"type": "website", "name": "string", "url": "https://...", "for_skill": "string"}]
        }
      ]
    }
  ],
  "resources": [{"type": "video", "name": "string", "url": "https://...", "for_skill": "string"}]
}"""

USER_PROMPT_TEMPLATE = """Design a complete study plan based on the goal and its feasibility analysis below.

GOAL: {topic}
CURRENT LEVEL: {current_level}
TARGET: {target}
DEADLINE: {deadline_months} months
WORK HOURS: {work_hours_start}-{work_hours_end}
WORK DAYS: {work_days}
PREFERRED STUDY TIME: {preferred_study_time}
MAX SESSION: {max_session_minutes} minutes
UNAVAILABLE DAYS: {unavailable_days}

FEASIBILITY ANALYSIS:
- verdict: {verdict}
- required_hours: {required_hours}
- available_hours: {available_hours}
- gap_hours: {gap_hours}
- analysis: {analysis}
- recommendations: {recommendations}
- benchmark_source: {benchmark_source}"""


class _LLMPlanOutput(BaseModel):
    # Struktur JSON yang diminta dari LLM.
    goal_summary: str
    total_weeks: int
    milestones: list[Milestone]
    weekly_schedule: list[WeekSchedule]
    resources: list[Resource]


def _build_system_prompt() -> str:
    # System message = static (persona + instructions + JSON schema) → prefix stabil
    # untuk context caching.
    instructions = INSTRUCTIONS_TEMPLATE.replace("__DETAILED_WEEKS__", str(DETAILED_WEEKS))
    return f"{SYSTEM_PROMPT}\n\n{instructions}"


def _build_user_prompt(request: PlanRequest, extra_notes: str | None = None) -> str:
    goal = request.goal
    feas = request.feasibility_result
    prompt = USER_PROMPT_TEMPLATE.format(
        topic=goal.topic,
        current_level=goal.current_level,
        target=goal.target,
        deadline_months=goal.deadline_months,
        work_hours_start=goal.work_hours_start,
        work_hours_end=goal.work_hours_end,
        work_days=", ".join(goal.work_days),
        preferred_study_time=goal.preferred_study_time,
        max_session_minutes=goal.max_session_minutes,
        unavailable_days=", ".join(goal.unavailable_days) or "none",
        verdict=feas.verdict,
        required_hours=feas.required_hours,
        available_hours=feas.available_hours,
        gap_hours=feas.gap_hours,
        analysis=feas.analysis,
        recommendations="; ".join(feas.recommendations) or "none",
        benchmark_source=feas.benchmark_source or "estimate",
    )
    if extra_notes:
        prompt += f"\n\nADDITIONAL CONSTRAINTS:\n{extra_notes}\n"
    return prompt


def persist_plan(
    output: _LLMPlanOutput,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
    *,
    version: int = 1,
    supersede_plan_id: uuid.UUID | None = None,
    reason: str = "initial",
) -> tuple[uuid.UUID, datetime]:
    # Simpan plan ke DB. Kalau supersede_plan_id diisi, plan lama ditandai "superseded".
    with SessionLocal() as db:
        plan = StudyPlan(
            goal_id=goal_id,
            user_id=user_id,
            plan_data=output.model_dump(mode="json"),
            status="active",
            version=version,
            reason=reason,
        )
        db.add(plan)
        db.flush()  # dapatkan id plan baru sebelum menautkan plan lama
        if supersede_plan_id is not None:
            old = db.get(StudyPlan, supersede_plan_id)
            if old is not None and old.user_id == user_id:
                old.status = "superseded"
                old.superseded_by = plan.id
        db.commit()
        db.refresh(plan)
        logger.info("Plan disimpan ke DB: plan_id=%s version=%d reason=%s", plan.id, plan.version, plan.reason)
        return plan.id, plan.created_at


def _latest_plan_meta(
    user_id: uuid.UUID, goal_id: uuid.UUID
) -> tuple[uuid.UUID, int] | None:
    # (id, version) plan dengan versi tertinggi untuk goal ini — atau None.
    with SessionLocal() as db:
        row = db.execute(
            select(StudyPlan.id, StudyPlan.version)
            .where(StudyPlan.goal_id == goal_id, StudyPlan.user_id == user_id)
            .order_by(StudyPlan.version.desc())
            .limit(1)
        ).first()
        return (row[0], row[1]) if row else None


async def generate_plan_output(
    request: PlanRequest,
    extra_notes: str | None = None,
    *,
    reasoning_effort: str | None = None,
) -> _LLMPlanOutput:
    # Panggil LLM untuk menghasilkan output plan (dipakai juga oleh reschedule).
    llm_response = await llm.chat_completion_json(
        _build_user_prompt(request, extra_notes),
        system=_build_system_prompt(),
        schema=_LLMPlanOutput,
        temperature=0.7,
        max_tokens=PLAN_MAX_TOKENS,
        reasoning_effort=reasoning_effort or PLAN_REASONING_EFFORT,
        thinking=True,
    )
    if llm_response.finish_reason == "length":
        logger.warning(
            "Plan generation output truncated (finish_reason=length, tokens=%s). "
            "Pertimbangkan menaikkan max_tokens atau menurunkan DETAILED_WEEKS.",
            llm_response.usage.model_dump(),
        )
    return _LLMPlanOutput.model_validate(llm_response.data)


def verify_goal_ownership(user_id: uuid.UUID, goal_id: uuid.UUID) -> Goal:
    # Ambil goal milik user; raise 404 kalau tidak ada / bukan miliknya.
    with SessionLocal() as db:
        goal = db.scalar(
            select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id)
        )
        if goal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found."
            )
        return goal


def build_feasibility_request(goal: Goal) -> FeasibilityRequest:
    # Bangun FeasibilityRequest dari Goal yang tersimpan di DB.
    return FeasibilityRequest(
        topic=goal.topic,
        current_level=goal.current_level or "unspecified",
        target=goal.target or goal.topic,
        deadline_months=goal.deadline_months or 1,
        work_hours_start=goal.work_hours_start.strftime("%H:%M")
        if goal.work_hours_start
        else "00:00",
        work_hours_end=goal.work_hours_end.strftime("%H:%M")
        if goal.work_hours_end
        else "23:59",
        work_days=goal.work_days or ["monday", "tuesday", "wednesday", "thursday", "friday"],
        preferred_study_time=goal.preferred_study_time or "evening",
        max_session_minutes=goal.max_session_minutes or 60,
        unavailable_days=goal.unavailable_days or [],
    )


def _to_response(
    output: _LLMPlanOutput,
    *,
    plan_id: uuid.UUID,
    created_at: datetime,
    version: int = 1,
    status: str = "active",
    reason: str = "initial",
) -> PlanResponse:
    return PlanResponse(
        plan_id=plan_id,
        goal_summary=output.goal_summary,
        total_weeks=output.total_weeks,
        milestones=output.milestones,
        weekly_schedule=output.weekly_schedule,
        resources=output.resources,
        created_at=created_at,
        version=version,
        status=status,
        reason=reason,
    )


def _parse_output(content: str, finish_reason: str | None) -> _LLMPlanOutput:
    # Parse + validasi output LLM; beri pesan jelas kalau output terpotong.
    try:
        return _LLMPlanOutput.model_validate_json(content)
    except Exception as exc:  # noqa: BLE001 - diteruskan ke caller sebagai error jelas
        if finish_reason == "length":
            raise ValueError(
                "LLM output was truncated (finish_reason=length). Increase max_tokens, "
                "reduce DETAILED_WEEKS, or shorten the deadline scope, then retry."
            ) from exc
        raise


async def generate_plan(
    request: PlanRequest, user_id: uuid.UUID, goal_id: uuid.UUID
) -> PlanResponse:
    # Mode non-streaming: hasilkan plan lengkap lalu simpan ke DB.
    # Verifikasi kepemilikan goal sebelum memanggil LLM (404 kalau bukan milik user).
    verify_goal_ownership(user_id, goal_id)

    logger.info(
        "Generate plan: user_id=%s goal_id=%s topic=%r target=%r deadline_months=%d verdict=%s detailed_weeks=%d",
        user_id,
        goal_id,
        request.goal.topic,
        request.goal.target,
        request.goal.deadline_months,
        request.feasibility_result.verdict,
        DETAILED_WEEKS,
    )

    output = await generate_plan_output(request)

    # Versioning: kalau goal ini sudah punya plan, buat versi baru & supersede yang lama
    # (konsisten dengan reschedule). Ini mencegah regenerate "menimpa"/menghilangkan versi.
    latest = _latest_plan_meta(user_id, goal_id)
    if latest is not None:
        version = latest[1] + 1
        supersede_plan_id: uuid.UUID | None = latest[0]
        reason = "regenerate"
    else:
        version = 1
        supersede_plan_id = None
        reason = "initial"

    plan_id, created_at = persist_plan(
        output,
        user_id,
        goal_id,
        version=version,
        supersede_plan_id=supersede_plan_id,
        reason=reason,
    )

    logger.info(
        "Plan selesai: plan_id=%s version=%d reason=%s total_weeks=%d milestones=%d weeks_scheduled=%d resources=%d",
        plan_id,
        version,
        reason,
        output.total_weeks,
        len(output.milestones),
        len(output.weekly_schedule),
        len(output.resources),
    )
    return _to_response(
        output,
        plan_id=plan_id,
        created_at=created_at,
        version=version,
        status="active",
        reason=reason,
    )


def _sse_frame(text: str) -> str:
    # Format SSE standar. Baris baru dipecah menjadi beberapa `data:` (SSE multi-line).
    lines = text.split("\n")
    return "".join(f"data: {line}\n" for line in lines) + "\n"


async def generate_plan_stream(
    request: PlanRequest, user_id: uuid.UUID, goal_id: uuid.UUID
) -> AsyncIterator[str]:
    # Mode streaming: kirim chunk sebagai SSE, lalu simpan plan setelah stream selesai.
    # Ownership sudah diverifikasi di endpoint (agar error 404 bisa dikembalikan sebelum stream).
    logger.info(
        "Generate plan (stream): user_id=%s goal_id=%s topic=%r",
        user_id,
        goal_id,
        request.goal.topic,
    )

    buffer: list[str] = []
    async for chunk in llm.chat_completion_stream(
        _build_user_prompt(request),
        system=_build_system_prompt(),
        temperature=0.7,
        max_tokens=PLAN_MAX_TOKENS,
        reasoning_effort=PLAN_REASONING_EFFORT,
        thinking=True,
    ):
        buffer.append(chunk)
        yield _sse_frame(chunk)

    content = "".join(buffer)
    try:
        output = _parse_output(content, finish_reason=None)
        latest = _latest_plan_meta(user_id, goal_id)
        if latest is not None:
            version = latest[1] + 1
            supersede_plan_id: uuid.UUID | None = latest[0]
            reason = "regenerate"
        else:
            version = 1
            supersede_plan_id = None
            reason = "initial"
        plan_id, _ = persist_plan(
            output,
            user_id,
            goal_id,
            version=version,
            supersede_plan_id=supersede_plan_id,
            reason=reason,
        )
        logger.info("Plan (stream) selesai & disimpan: plan_id=%s version=%d", plan_id, version)
    except Exception as exc:  # noqa: BLE001 - laporkan ke client via SSE, jangan putus koneksi
        logger.exception("Finalisasi plan (stream) gagal")
        yield _sse_frame(f"[ERROR] {exc}")

    yield _sse_frame("[DONE]")


def get_plan(plan_id: uuid.UUID, user_id: uuid.UUID) -> PlanResponse | None:
    # Ambil plan milik user dari DB dan rekonstruksi PlanResponse (404 kalau bukan miliknya).
    with SessionLocal() as db:
        plan = db.get(StudyPlan, plan_id)
        if plan is None or plan.user_id != user_id:
            return None
        data = plan.plan_data or {}
        return PlanResponse(
            plan_id=plan.id,
            created_at=plan.created_at,
            version=plan.version,
            status=plan.status,
            reason=plan.reason,
            **data,
        )


def get_latest_plan_for_goal(user_id: uuid.UUID, goal_id: uuid.UUID) -> PlanResponse | None:
    # Ambil plan terbaru (versi tertinggi) milik user untuk sebuah goal.
    return get_plan_by_goal_version(user_id, goal_id)


def get_plan_by_goal_version(
    user_id: uuid.UUID, goal_id: uuid.UUID, version: int | None = None
) -> PlanResponse | None:
    # Kalau version diisi → plan versi itu. Kalau tidak → versi tertinggi (terbaru).
    with SessionLocal() as db:
        stmt = select(StudyPlan).where(
            StudyPlan.goal_id == goal_id, StudyPlan.user_id == user_id
        )
        if version is not None:
            stmt = stmt.where(StudyPlan.version == version)
        else:
            stmt = stmt.order_by(StudyPlan.version.desc()).limit(1)
        plan = db.scalar(stmt)
        if plan is None:
            return None
        data = plan.plan_data or {}
        return PlanResponse(
            plan_id=plan.id,
            created_at=plan.created_at,
            version=plan.version,
            status=plan.status,
            reason=plan.reason,
            **data,
        )


def list_plan_versions(user_id: uuid.UUID, goal_id: uuid.UUID) -> list[PlanVersion]:
    # Semua versi plan untuk goal (urut versi menaik) — untuk Plan History.
    with SessionLocal() as db:
        plans = db.scalars(
            select(StudyPlan)
            .where(StudyPlan.goal_id == goal_id, StudyPlan.user_id == user_id)
            .order_by(StudyPlan.version.asc())
        ).all()
        return [
            PlanVersion(
                plan_id=plan.id,
                version=plan.version,
                status=plan.status,
                reason=plan.reason,
                created_at=plan.created_at,
                total_weeks=(plan.plan_data or {}).get("total_weeks", 0),
                goal_summary=(plan.plan_data or {}).get("goal_summary", ""),
            )
            for plan in plans
        ]
