# Service F-03 — Study Plan Generator.
# Membuat study plan (milestones + jadwal mingguan + resources) memakai LLM,
# lalu menyimpannya ke tabel `study_plans` (kolom plan_data JSONB).

import json
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

SYSTEM_PROMPT = """You are Study Agent, an expert learning plan designer. Always respond in __LANGUAGE__."""

LANGUAGE_NAMES = {"en": "English", "id": "Bahasa Indonesia", "zh": "Simplified Chinese (中文)"}

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
8. Do not add extra top-level keys. All text in __LANGUAGE__. Respond ONLY with a JSON object.

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


def _build_system_prompt(language: str = "en") -> str:
    # System message = static (persona + instructions + JSON schema) → prefix stabil
    # untuk context caching; bahasa output disuntikkan dari pilihan user.
    instructions = INSTRUCTIONS_TEMPLATE.replace("__DETAILED_WEEKS__", str(DETAILED_WEEKS))
    language_name = LANGUAGE_NAMES.get((language or "en").lower(), "English")
    text = f"{SYSTEM_PROMPT}\n\n{instructions}"
    return text.replace("__LANGUAGE__", language_name)


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
        system=_build_system_prompt(request.language),
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


def build_feasibility_request(goal: Goal, language: str = "en") -> FeasibilityRequest:
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
        language=language if language in {"en", "id", "zh"} else "en",
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


def _sse_json(payload: dict) -> str:
    # Satu frame SSE berisi JSON (status / delta / plan / error).
    return f"data: {json.dumps(payload)}\n\n"


async def generate_plan_stream(
    request: PlanRequest, user_id: uuid.UUID, goal_id: uuid.UUID
) -> AsyncIterator[str]:
    # Mode streaming terstruktur:
    #   {"type":"status"}  → tahapan progres
    #   {"type":"delta"}   → potongan teks dari LLM (real-time)
    #   {"type":"plan"}    → plan final (JSON lengkap)
    #   {"type":"error"}   → error yang tidak memutus koneksi
    logger.info(
        "Generate plan (stream): user_id=%s goal_id=%s topic=%r",
        user_id,
        goal_id,
        request.goal.topic,
    )

    yield _sse_json({"type": "status", "stage": "Analyzing your goal..."})

    buffer: list[str] = []
    chars = 0
    emitted = 0
    stages = [
        (1800, "Designing milestones..."),
        (4000, "Building weekly schedule..."),
        (7000, "Selecting resources..."),
    ]

    async for chunk in llm.chat_completion_stream(
        _build_user_prompt(request),
        system=_build_system_prompt(request.language),
        temperature=0.7,
        max_tokens=PLAN_MAX_TOKENS,
        reasoning_effort=PLAN_REASONING_EFFORT,
        thinking=True,
    ):
        buffer.append(chunk)
        chars += len(chunk)
        while emitted < len(stages) and chars >= stages[emitted][0]:
            yield _sse_json({"type": "status", "stage": stages[emitted][1]})
            emitted += 1
        yield _sse_json({"type": "delta", "content": chunk})

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
        plan_id, created_at = persist_plan(
            output,
            user_id,
            goal_id,
            version=version,
            supersede_plan_id=supersede_plan_id,
            reason=reason,
        )
        plan = _to_response(
            output,
            plan_id=plan_id,
            created_at=created_at,
            version=version,
            status="active",
            reason=reason,
        )
        logger.info("Plan (stream) selesai & disimpan: plan_id=%s version=%d", plan_id, version)
        yield _sse_json({"type": "plan", "plan": plan.model_dump(mode="json")})
    except Exception as exc:  # noqa: BLE001 - laporkan ke client via SSE, jangan putus koneksi
        logger.exception("Finalisasi plan (stream) gagal")
        yield _sse_json({"type": "error", "message": str(exc)})

    yield "data: [DONE]\n\n"


class _LLMNextMonthOutput(BaseModel):
    # Output AI untuk penjadwalan bulan berikutnya.
    weeks: list[WeekSchedule]


NEXT_MONTH_PROMPT = """You are extending an existing study plan. Generate ONLY the next block of weeks.

GOAL: {topic}
TARGET: {target}
DEADLINE: {deadline_months} months (total {total_weeks} weeks)
MILESTONE — Month {month}:
- focus: {focus}
- target: {milestone_target}
- checkpoint: {checkpoint}
PREVIOUS WEEKS:
{previous_weeks}

TASK:
- Generate a detailed day-by-day schedule for weeks {start}-{end} (exactly {count} weeks).
- Continue the week numbering from {start}.
- Continue "date_offset" starting at {next_offset} (days from plan start).
- Respect the user's work hours ({work_hours_start}-{work_hours_end}), available days, preferred study time ({preferred_study_time}), and max session ({max_session_minutes} minutes).
- Align topics with the milestone above.
- Keep each field concise; all text in {language}.

Respond ONLY with JSON:
{{"weeks": [{{"week": {start}, "theme": "string", "days": [{{"day": "Monday", "date_offset": {next_offset}, "time": "19:00", "topic": "string", "duration_minutes": 60, "activities": ["string"], "resources": [{{"type": "website", "name": "string", "url": "https://...", "for_skill": "string"}}]}}]}}]}}"""


async def generate_next_month(
    user_id: uuid.UUID, plan_id: uuid.UUID, language: str = "en"
) -> PlanResponse:
    # Lazy generation: buat jadwal 4 minggu berikutnya lalu append ke plan_data.
    with SessionLocal() as db:
        plan = db.scalar(
            select(StudyPlan).where(
                StudyPlan.id == plan_id, StudyPlan.user_id == user_id
            )
        )
        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found."
            )
        goal = db.get(Goal, plan.goal_id)
        data = dict(plan.plan_data or {})

    weeks = list(data.get("weekly_schedule") or [])
    if not weeks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This plan has no weekly schedule yet.",
        )

    total_weeks = int(data.get("total_weeks") or 0)
    last_week = max(int(week.get("week") or 0) for week in weeks)
    start = last_week + 1
    if total_weeks and start > total_weeks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All weeks are already scheduled.",
        )
    end = min(start + 3, total_weeks) if total_weeks else start + 3
    count = end - start + 1
    month = ((start - 1) // 4) + 1

    milestones = data.get("milestones") or []
    milestone = next(
        (item for item in milestones if item.get("month") == month), None
    ) or {}
    next_offset = (
        max(
            (
                int(day.get("date_offset") or 0)
                for week in weeks
                for day in week.get("days", [])
            ),
            default=-1,
        )
        + 1
    )
    previous_weeks = "\n".join(
        f"Week {week.get('week')}: {week.get('theme')}" for week in weeks[-4:]
    )

    language_name = LANGUAGE_NAMES.get((language or "en").lower(), "English")
    prompt = NEXT_MONTH_PROMPT.format(
        topic=goal.topic if goal else "—",
        target=(goal.target if goal else None) or "—",
        deadline_months=(goal.deadline_months if goal else None) or "?",
        total_weeks=total_weeks or "?",
        month=month,
        focus=milestone.get("focus", "—"),
        milestone_target=milestone.get("target", "—"),
        checkpoint=milestone.get("checkpoint", "—"),
        previous_weeks=previous_weeks or "(first month)",
        start=start,
        end=end,
        count=count,
        next_offset=next_offset,
        work_hours_start=(
            goal.work_hours_start.strftime("%H:%M") if goal and goal.work_hours_start else "09:00"
        ),
        work_hours_end=(
            goal.work_hours_end.strftime("%H:%M") if goal and goal.work_hours_end else "18:00"
        ),
        preferred_study_time=(goal.preferred_study_time if goal else None) or "evening",
        max_session_minutes=(goal.max_session_minutes if goal else None) or 60,
        language=language_name,
    )

    logger.info(
        "Generate next month: plan_id=%s weeks=%d-%d language=%s",
        plan_id,
        start,
        end,
        language,
    )
    response = await llm.chat_completion_json(
        prompt,
        system=(
            "You are Study Agent, an expert learning plan designer. "
            f"Always respond in {language_name}. "
            'Output JSON only, matching exactly: {"weeks": [ ... ]}.'
        ),
        schema=_LLMNextMonthOutput,
        temperature=0.7,
        max_tokens=PLAN_MAX_TOKENS,
        reasoning_effort=PLAN_REASONING_EFFORT,
        thinking=True,
    )
    output = _LLMNextMonthOutput.model_validate(response.data)

    existing_numbers = {int(week.get("week") or 0) for week in weeks}
    new_weeks = [
        week.model_dump(mode="json")
        for week in output.weeks
        if start <= week.week <= end and week.week not in existing_numbers
    ]
    if not new_weeks:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI did not return any new weeks.",
        )

    merged = sorted(weeks + new_weeks, key=lambda week: int(week.get("week") or 0))
    data["weekly_schedule"] = merged

    with SessionLocal() as db:
        plan = db.get(StudyPlan, plan_id)
        if plan is None or plan.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found."
            )
        plan.plan_data = data
        db.commit()

    logger.info(
        "Next month ditambahkan: plan_id=%s new_weeks=%d total=%d",
        plan_id,
        len(new_weeks),
        len(merged),
    )
    updated = get_plan(plan_id, user_id)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found."
        )
    return updated


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
