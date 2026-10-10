# Service F-05 — Adaptive Reschedule.
# Menganalisis keterlambatan user, menawarkan 4 strategi adaptasi (LLM),
# lalu membuat ulang plan dengan constraint baru (versi baru, plan lama disimpan).

import logging
import math
import uuid

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.goal import Goal
from app.models.progress_entry import ProgressEntry
from app.models.study_plan import StudyPlan
from app.core.config import settings
from app.schemas.feasibility import FeasibilityResponse
from app.schemas.plan import PlanRequest
from app.schemas.reschedule import (
    RescheduleAnalysis,
    RescheduleOption,
    RescheduleRequest,
    RescheduleResult,
)
from app.services import feasibility_service, llm, plan_service

logger = logging.getLogger(__name__)

ANALYSIS_MAX_TOKENS = 8192

SYSTEM_PROMPT = """You are Study Agent, an adaptive learning plan coach. Always respond in English."""

ANALYZE_PROMPT = """A learner is falling behind on their study plan. Analyze the situation and propose exactly 4 adaptation options.

GOAL:
- Topic: {topic}
- Target: {target}
- Deadline: {deadline_months} months ({total_weeks} weeks scheduled)

PROGRESS:
- Completion rate: {completion_rate_pct}%
- Sessions: {completed} completed, {skipped} skipped, {pending} pending (total {total_sessions})
- Current streak: {current_streak}
- Weeks behind: {weeks_behind}
- Longest run of skipped sessions: {consecutive_skipped}

INSTRUCTIONS:
- Provide one option for EACH of these exact types: REBALANCE, EXTEND, REDUCE, INTENSIFY.
  * REBALANCE: redistribute remaining material across the remaining weeks, same deadline.
  * EXTEND: extend the deadline and spread the material.
  * REDUCE: reduce scope, target a smaller achievable outcome.
  * INTENSIFY: increase daily session length to cover the material faster.
- For each option give: type, title (short), description (what changes), trade_offs (downside), estimated_new_deadline (human readable or null).
- Be supportive, realistic, concise. All text in English.
- "reason" = one or two sentences explaining why adaptation is recommended now.

Respond ONLY with a JSON object:
{{
  "reason": "string",
  "options": [
    {{"type": "REBALANCE", "title": "string", "description": "string", "trade_offs": "string", "estimated_new_deadline": null}},
    {{"type": "EXTEND", "title": "string", "description": "string", "trade_offs": "string", "estimated_new_deadline": "string"}},
    {{"type": "REDUCE", "title": "string", "description": "string", "trade_offs": "string", "estimated_new_deadline": null}},
    {{"type": "INTENSIFY", "title": "string", "description": "string", "trade_offs": "string", "estimated_new_deadline": null}}
  ]
}}
"""

# Template cadangan kalau LLM tidak melengkapi keempat opsi.
DEFAULT_OPTIONS: dict[str, RescheduleOption] = {
    "REBALANCE": RescheduleOption(
        type="REBALANCE",
        title="Re-balance schedule",
        description="Redistribute the remaining material across the remaining weeks.",
        trade_offs="Some weeks become denser; you must keep pace.",
        estimated_new_deadline=None,
    ),
    "EXTEND": RescheduleOption(
        type="EXTEND",
        title="Extend deadline",
        description="Push the deadline back and spread the material more thinly.",
        trade_offs="You reach the goal later than planned.",
        estimated_new_deadline="Later than the original deadline",
    ),
    "REDUCE": RescheduleOption(
        type="REDUCE",
        title="Reduce scope",
        description="Focus on essential core skills and a smaller target.",
        trade_offs="You cover less material or a lower target level.",
        estimated_new_deadline=None,
    ),
    "INTENSIFY": RescheduleOption(
        type="INTENSIFY",
        title="Intensify sessions",
        description="Study longer per session to catch up within the same deadline.",
        trade_offs="Higher daily effort and risk of burnout.",
        estimated_new_deadline=None,
    ),
}


class _LLMAnalysisOutput(BaseModel):
    reason: str
    options: list[RescheduleOption]


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")


def _get_owned_plan(db: Session, user_id: uuid.UUID, plan_id: uuid.UUID) -> StudyPlan:
    plan = db.scalar(
        select(StudyPlan).where(StudyPlan.id == plan_id, StudyPlan.user_id == user_id)
    )
    if plan is None:
        raise _not_found()
    return plan


def _ordered_statuses(plan: StudyPlan) -> list[str]:
    # Status tiap sesi sesuai urutan jadwal (plan_data + progress entries).
    data = plan.plan_data or {}
    keys: list[tuple[int, str, int]] = []
    for week in data.get("weekly_schedule", []):
        for index, day in enumerate(week.get("days", [])):
            keys.append((week.get("week", 1), day.get("day", ""), index))

    with SessionLocal() as db:
        entries = db.scalars(
            select(ProgressEntry).where(ProgressEntry.plan_id == plan.id)
        ).all()
    by_key = {(e.week_number, e.day_name, e.session_index): e.status for e in entries}
    return [by_key.get(key, "pending") for key in keys]


def _longest_skipped_run(statuses: list[str]) -> int:
    best = 0
    current = 0
    for value in statuses:
        current = current + 1 if value == "skipped" else 0
        best = max(best, current)
    return best


def _compute_metrics(plan: StudyPlan) -> dict:
    statuses = _ordered_statuses(plan)
    total = len(statuses)
    completed = statuses.count("completed")
    skipped = statuses.count("skipped")
    pending = total - completed - skipped
    total_weeks = (plan.plan_data or {}).get("total_weeks") or 0
    sessions_per_week = (total / total_weeks) if total_weeks else total
    weeks_behind = int(skipped // sessions_per_week) if sessions_per_week else 0
    marked = completed + skipped
    marked_rate = (completed / marked) if marked else 0.0
    completion_rate = (completed / total) if total else 0.0
    return {
        "statuses": statuses,
        "total": total,
        "completed": completed,
        "skipped": skipped,
        "pending": pending,
        "total_weeks": total_weeks,
        "weeks_behind": weeks_behind,
        "consecutive_skipped": _longest_skipped_run(statuses),
        "completion_rate": completion_rate,
        "marked_rate": marked_rate,
    }


def _ensure_four_options(options: list[RescheduleOption]) -> list[RescheduleOption]:
    by_type: dict[str, RescheduleOption] = {opt.type: opt for opt in options}
    return [by_type.get(key, DEFAULT_OPTIONS[key]) for key in DEFAULT_OPTIONS]


async def analyze_progress(user_id: uuid.UUID, plan_id: uuid.UUID) -> RescheduleAnalysis:
    # Analisis keterlambatan + opsi adaptasi (LLM).
    with SessionLocal() as db:
        plan = _get_owned_plan(db, user_id, plan_id)
        goal = db.get(Goal, plan.goal_id)
    metrics = _compute_metrics(plan)

    should = metrics["completed"] + metrics["skipped"] > 0 and (
        metrics["marked_rate"] < 0.8
        or metrics["consecutive_skipped"] >= 3
        or metrics["weeks_behind"] >= 1
    )

    logger.info(
        "Reschedule analyze: plan_id=%s should=%s rate=%.2f weeks_behind=%d skipped_run=%d",
        plan_id,
        should,
        metrics["completion_rate"],
        metrics["weeks_behind"],
        metrics["consecutive_skipped"],
    )

    prompt = ANALYZE_PROMPT.format(
        topic=goal.topic if goal else "—",
        target=(goal.target if goal else None) or "—",
        deadline_months=(goal.deadline_months if goal else None) or "?",
        total_weeks=metrics["total_weeks"],
        completion_rate_pct=round(metrics["completion_rate"] * 100),
        completed=metrics["completed"],
        skipped=metrics["skipped"],
        pending=metrics["pending"],
        total_sessions=metrics["total"],
        current_streak=0,
        weeks_behind=metrics["weeks_behind"],
        consecutive_skipped=metrics["consecutive_skipped"],
    )

    llm_response = await llm.chat_completion_json(
        prompt,
        system=SYSTEM_PROMPT,
        schema=_LLMAnalysisOutput,
        temperature=0.5,
        max_tokens=ANALYSIS_MAX_TOKENS,
        reasoning_effort="high",
        thinking=True,
    )
    output = _LLMAnalysisOutput.model_validate(llm_response.data)
    options = _ensure_four_options(output.options)

    default_reason = (
        "You've been falling behind on recent sessions. Adapting the plan now "
        "keeps your goal achievable."
    )
    return RescheduleAnalysis(
        should_reschedule=should,
        reason=output.reason.strip() or default_reason,
        completion_rate=round(metrics["completion_rate"], 3),
        weeks_behind=metrics["weeks_behind"],
        options=options,
    )


def _adjust_request(
    feas_request, option_type: str, additional_params: dict
) -> tuple[list[str], list[str]]:
    # Kembalikan (changes, extra_notes) sesuai opsi adaptasi.
    if option_type == "EXTEND":
        weeks_behind = int(additional_params.get("weeks_behind") or 0)
        extra_months = int(
            additional_params.get("extra_months") or max(1, math.ceil(weeks_behind / 4))
        )
        feas_request.deadline_months += extra_months
        changes = [f"Extended deadline by {extra_months} month(s)"]
        notes = [
            f"Extend the deadline by {extra_months} month(s) and spread all material accordingly.",
            "Keep session length and weekly rhythm unchanged; add more weeks instead.",
        ]
    elif option_type == "REDUCE":
        changes = ["Reduced scope to essential core topics"]
        notes = [
            "Reduce the scope: cover only the essential core skills.",
            "Lower the target to a smaller, clearly achievable outcome within the deadline.",
        ]
    elif option_type == "INTENSIFY":
        extra_minutes = int(additional_params.get("extra_minutes") or 30)
        feas_request.max_session_minutes = min(240, feas_request.max_session_minutes + extra_minutes)
        changes = [f"Increased session length to {feas_request.max_session_minutes} minutes"]
        notes = [
            f"Increase daily session length to {feas_request.max_session_minutes} minutes.",
            "Cover the same material faster within the original deadline.",
        ]
    else:  # REBALANCE
        changes = ["Redistributed remaining material across the remaining weeks"]
        notes = [
            "Keep the same deadline and session length.",
            "Redistribute all remaining material across the remaining weeks and prioritize catch-up.",
        ]
    return changes, notes


async def apply_reschedule(
    user_id: uuid.UUID, plan_id: uuid.UUID, request: RescheduleRequest
) -> RescheduleResult:
    # Buat plan baru (versi berikutnya) sesuai opsi adaptasi.
    with SessionLocal() as db:
        plan = _get_owned_plan(db, user_id, plan_id)
        goal = db.get(Goal, plan.goal_id)
        old_version = plan.version
    if goal is None:
        raise _not_found()

    metrics = _compute_metrics(plan)
    feasibility_request = plan_service.build_feasibility_request(goal)
    changes, notes = _adjust_request(
        feasibility_request,
        request.option_type,
        {**request.additional_params, "weeks_behind": metrics["weeks_behind"]},
    )

    available_hours = feasibility_service.compute_available_hours(feasibility_request)
    feasibility_result = FeasibilityResponse(
        feasible=True,
        confidence=0.7,
        required_hours=available_hours,
        available_hours=available_hours,
        gap_hours=0,
        verdict="REALISTIC_WITH_NOTES",
        analysis=f"Re-planned via adaptive reschedule ({request.option_type}).",
        recommendations=[],
        benchmark_source="estimate",
        requires_manual_review=False,
    )
    plan_request = PlanRequest(
        goal=feasibility_request, feasibility_result=feasibility_result
    )

    logger.info(
        "Reschedule apply: plan_id=%s option=%s version %d -> %d",
        plan_id,
        request.option_type,
        old_version,
        old_version + 1,
    )

    output = await plan_service.generate_plan_output(
        plan_request,
        extra_notes=" ".join(notes),
        reasoning_effort=settings.reschedule_apply_reasoning_effort,
    )
    new_version = old_version + 1
    new_plan_id, _ = plan_service.persist_plan(
        output,
        user_id,
        goal.id,
        version=new_version,
        supersede_plan_id=plan_id,
        reason="reschedule",
    )

    changes.append(f"Created plan version v{new_version}")
    logger.info("Reschedule selesai: new_plan_id=%s version=%d", new_plan_id, new_version)
    return RescheduleResult(
        plan_id=new_plan_id,
        summary=output.goal_summary,
        changes=changes,
        version=new_version,
    )
