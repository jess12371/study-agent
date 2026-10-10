# Service F-11 — Agent Dialog (chat context-aware + action buttons).

import json
import logging
import uuid
from collections.abc import AsyncIterator

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.chat_message import ChatMessage as ChatMessageModel
from app.models.goal import Goal
from app.models.resource import Resource
from app.models.study_plan import StudyPlan
from app.schemas.chat import (
    ChatAction,
    ChatActionRequest,
    ChatActionResult,
    ChatMessage,
    ChatResponse,
)
from app.schemas.reschedule import RescheduleRequest
from app.services import feasibility_service, llm, plan_service, progress_service, reschedule_service

logger = logging.getLogger(__name__)

HISTORY_LIMIT = 20
CHAT_MAX_TOKENS = 1500

SYSTEM_PROMPT = """You are Study Agent, a helpful AI learning assistant.

CONTEXT:
- Goal: __GOAL_TOPIC__ -> __GOAL_TARGET__
- Current Plan: v__PLAN_VERSION__, __TOTAL_WEEKS__ weeks
- Progress: __COMPLETION_RATE__% complete, __HOURS_STUDIED__h studied
- Recent issues: __PROGRESS_ISSUES__

CAPABILITIES:
1. Answer questions about the plan
2. Suggest modifications (return as action buttons)
3. Discuss progress & motivation
4. Recommend resources

RULES:
- Respond in same language as user (EN or ZH)
- Be supportive & realistic
- If user asks to modify plan, present 2-3 options as action buttons
- Don't hallucinate — if unsure, say so
- Keep responses concise (< 200 words)

OUTPUT FORMAT (JSON):
{
  "message": "your response text",
  "actions": [
    {"type": "modify_plan", "label": "Extend deadline", "payload": {"option": "extend"}}
  ]
}

Allowed action types: "modify_plan" (payload.option in rebalance/extend/reduce/intensify/regenerate) and "view_resource" (payload.resource_id). Omit actions when not needed."""


def _build_system_prompt(context: dict) -> str:
    # Pakai replace (bukan .format) karena prompt berisi contoh JSON dengan kurung kurawal.
    return (
        SYSTEM_PROMPT.replace("__GOAL_TOPIC__", str(context["goal_topic"]))
        .replace("__GOAL_TARGET__", str(context["goal_target"]))
        .replace("__PLAN_VERSION__", str(context["plan_version"]))
        .replace("__TOTAL_WEEKS__", str(context["total_weeks"]))
        .replace("__COMPLETION_RATE__", str(context["completion_rate"]))
        .replace("__HOURS_STUDIED__", str(context["hours_studied"]))
        .replace("__PROGRESS_ISSUES__", str(context["progress_issues"]))
    )


class _LLMChatOutput(BaseModel):
    message: str
    actions: list[ChatAction] = Field(default_factory=list)


def _not_found(detail: str = "Goal not found.") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _get_owned_goal(db: Session, user_id: uuid.UUID, goal_id: uuid.UUID) -> Goal:
    goal = db.scalar(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id)
    )
    if goal is None:
        raise _not_found()
    return goal


def _latest_plan(db: Session, user_id: uuid.UUID, goal_id: uuid.UUID) -> StudyPlan | None:
    return db.scalar(
        select(StudyPlan)
        .where(StudyPlan.goal_id == goal_id, StudyPlan.user_id == user_id)
        .order_by(StudyPlan.version.desc())
        .limit(1)
    )


def get_context(user_id: uuid.UUID, goal_id: uuid.UUID) -> dict:
    # Konteks untuk LLM: goal + plan terbaru + progress stats.
    with SessionLocal() as db:
        goal = _get_owned_goal(db, user_id, goal_id)
        plan = _latest_plan(db, user_id, goal_id)
        context = {
            "goal_topic": goal.topic,
            "goal_target": goal.target or "—",
            "goal_level": goal.current_level or "—",
            "plan_id": str(plan.id) if plan else None,
            "plan_version": plan.version if plan else 0,
            "total_weeks": (plan.plan_data or {}).get("total_weeks", 0) if plan else 0,
            "goal_summary": (plan.plan_data or {}).get("goal_summary", "") if plan else "",
            "completion_rate": 0.0,
            "hours_studied": 0.0,
            "completed": 0,
            "skipped": 0,
            "pending": 0,
        }
        if plan is not None:
            stats = progress_service.get_stats(db, user_id, plan.id)
            context.update(
                completion_rate=round(stats.completion_rate * 100),
                hours_studied=stats.total_hours,
                completed=stats.completed,
                skipped=stats.skipped,
                pending=stats.pending,
            )
        context["progress_issues"] = (
            f"{context['skipped']} skipped, {context['pending']} pending, "
            f"completion {context['completion_rate']}%"
            if plan is not None
            else "no plan yet"
        )
        return context


def _format_history(messages: list[ChatMessage]) -> str:
    if not messages:
        return "(no previous messages)"
    lines = []
    for msg in messages:
        speaker = "User" if msg.role == "user" else "Assistant"
        lines.append(f"{speaker}: {msg.content}")
    return "\n".join(lines)


def _save_message(
    db: Session,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
    role: str,
    content: str,
    actions: list[ChatAction] | None = None,
) -> ChatMessageModel:
    record = ChatMessageModel(
        user_id=user_id,
        goal_id=goal_id,
        role=role,
        content=content,
        actions=[a.model_dump() for a in actions] if actions else None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_history(user_id: uuid.UUID, goal_id: uuid.UUID) -> list[ChatMessage]:
    with SessionLocal() as db:
        _get_owned_goal(db, user_id, goal_id)
        records = db.scalars(
            select(ChatMessageModel)
            .where(
                ChatMessageModel.user_id == user_id,
                ChatMessageModel.goal_id == goal_id,
            )
            .order_by(ChatMessageModel.created_at.asc())
        ).all()
        return [ChatMessage.model_validate(record) for record in records]


def clear_history(user_id: uuid.UUID, goal_id: uuid.UUID) -> None:
    with SessionLocal() as db:
        _get_owned_goal(db, user_id, goal_id)
        db.execute(
            delete(ChatMessageModel).where(
                ChatMessageModel.user_id == user_id,
                ChatMessageModel.goal_id == goal_id,
            )
        )
        db.commit()
    logger.info("Chat dibersihkan: user_id=%s goal_id=%s", user_id, goal_id)


async def send_message(user_id: uuid.UUID, goal_id: uuid.UUID, message: str) -> ChatResponse:
    # Kirim pesan user, panggil LLM context-aware, simpan & kembalikan respons.
    with SessionLocal() as db:
        _get_owned_goal(db, user_id, goal_id)
        _save_message(db, user_id, goal_id, "user", message)

    context = get_context(user_id, goal_id)
    history = get_history(user_id, goal_id)[-HISTORY_LIMIT:]

    system = _build_system_prompt(context)
    user_prompt = (
        f"CONVERSATION SO FAR:\n{_format_history(history)}\n\n"
        f"Respond to the last user message. Output JSON only."
    )

    logger.info("Chat request: user_id=%s goal_id=%s chars=%d", user_id, goal_id, len(message))
    llm_response = await llm.chat_completion_json(
        user_prompt,
        system=system,
        schema=_LLMChatOutput,
        temperature=0.7,
        max_tokens=CHAT_MAX_TOKENS,
        reasoning_effort="low",
        thinking=False,
    )
    output = _LLMChatOutput.model_validate(llm_response.data)

    actions = [action for action in output.actions if action.type in {"modify_plan", "view_resource"}]

    with SessionLocal() as db:
        record = _save_message(db, user_id, goal_id, "assistant", output.message, actions)
        saved = ChatMessage.model_validate(record)

    return ChatResponse(message=saved, actions=actions)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _chunk_text(text: str, size: int = 48) -> list[str]:
    # Pecah teks menjadi potongan kecil agar UI terasa "mengetik".
    words = text.split(" ")
    chunks: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > size and current:
            chunks.append(current + " ")
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        chunks.append(current)
    return chunks or [text]


async def stream_message(user_id: uuid.UUID, goal_id: uuid.UUID, message: str) -> AsyncIterator[str]:
    # SSE: kirim delta teks, lalu pesan final (id + actions), lalu [DONE].
    response = await send_message(user_id, goal_id, message)
    for chunk in _chunk_text(response.message.content):
        yield _sse({"type": "delta", "content": chunk})
    payload = {
        "type": "message",
        "message": {
            "id": str(response.message.id),
            "role": "assistant",
            "content": response.message.content,
            "created_at": response.message.created_at.isoformat(),
            "actions": [a.model_dump() for a in response.actions],
        },
    }
    yield _sse(payload)
    yield "data: [DONE]\n\n"


async def execute_action(
    user_id: uuid.UUID, goal_id: uuid.UUID, request: ChatActionRequest
) -> ChatActionResult:
    # Eksekusi action button dari agent.
    action_type = request.action_type
    payload = request.payload or {}

    if action_type == "view_resource":
        resource_id = payload.get("resource_id")
        if not resource_id:
            raise HTTPException(status_code=400, detail="resource_id is required.")
        with SessionLocal() as db:
            resource = db.get(Resource, uuid.UUID(str(resource_id)))
            if resource is None:
                raise _not_found("Resource not found.")
            data = {
                "id": str(resource.id),
                "topic": resource.topic,
                "type": resource.type,
                "name": resource.name,
                "url": resource.url,
                "level": resource.level,
                "is_free": resource.is_free,
                "description": resource.description,
                "skills": resource.skills or [],
            }
        return ChatActionResult(type=action_type, message=f"Here is: {data['name']}", data=data)

    if action_type == "modify_plan":
        option = str(payload.get("option", "")).lower()
        with SessionLocal() as db:
            _get_owned_goal(db, user_id, goal_id)
            plan = _latest_plan(db, user_id, goal_id)
        if plan is None:
            raise _not_found("No plan to modify yet.")

        if option == "regenerate":
            result = await _regenerate(user_id, goal_id)
            return result

        if option not in {"rebalance", "extend", "reduce", "intensify"}:
            raise HTTPException(status_code=400, detail="Unknown modify_plan option.")
        reschedule_result = await reschedule_service.apply_reschedule(
            user_id, plan.id, RescheduleRequest(option_type=option.upper())  # type: ignore[arg-type]
        )
        text = f"Done — created plan v{reschedule_result.version}."
        with SessionLocal() as db:
            _save_message(db, user_id, goal_id, "assistant", text, None)
        return ChatActionResult(
            type=action_type,
            message=text,
            data={
                "plan_id": str(reschedule_result.plan_id),
                "version": reschedule_result.version,
                "changes": reschedule_result.changes,
            },
        )

    raise HTTPException(status_code=400, detail="Unknown action_type.")


async def _regenerate(user_id: uuid.UUID, goal_id: uuid.UUID) -> ChatActionResult:
    # Regenerate plan (versi baru) dengan feasibility tersintesis (tanpa LLM tambahan).
    from app.schemas.feasibility import FeasibilityResponse
    from app.schemas.plan import PlanRequest

    with SessionLocal() as db:
        goal = _get_owned_goal(db, user_id, goal_id)
        plan = _latest_plan(db, user_id, goal_id)
    if goal is None:
        raise _not_found()

    feasibility_request = plan_service.build_feasibility_request(goal)
    available_hours = feasibility_service.compute_available_hours(feasibility_request)
    feasibility_result = FeasibilityResponse(
        feasible=True,
        confidence=0.7,
        required_hours=available_hours,
        available_hours=available_hours,
        gap_hours=0,
        verdict="REALISTIC_WITH_NOTES",
        analysis="Regenerated from chat.",
        recommendations=[],
        benchmark_source="estimate",
        requires_manual_review=False,
    )
    output = await plan_service.generate_plan_output(
        PlanRequest(goal=feasibility_request, feasibility_result=feasibility_result)
    )
    version = (plan.version + 1) if plan else 1
    new_plan_id, _ = plan_service.persist_plan(
        output,
        user_id,
        goal_id,
        version=version,
        supersede_plan_id=plan.id if plan else None,
        reason="regenerate",
    )
    text = f"Done — regenerated plan as v{version}."
    with SessionLocal() as db:
        _save_message(db, user_id, goal_id, "assistant", text, None)
    return ChatActionResult(
        type="modify_plan",
        message=text,
        data={"plan_id": str(new_plan_id), "version": version},
    )
