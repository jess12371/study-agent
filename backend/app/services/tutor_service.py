# Service Socratic Tutor — tanya jawab materi belajar (streaming) + quiz dari jadwal.

import json
import logging
import uuid
from collections.abc import AsyncIterator

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.study_plan import StudyPlan
from app.schemas.tutor import QuizQuestion, QuizResponse, TutorRequest
from app.services import llm

logger = logging.getLogger(__name__)

TUTOR_MAX_TOKENS = 1024
QUIZ_MAX_TOKENS = 2048

# System prompt STATIS diletakkan paling atas agar prefix bisa di-cache DeepSeek.
SYSTEM_PROMPT = """You are Study Agent Tutor, a Socratic learning coach.

RULES:
1. Answer in the same language as the student (English or Chinese).
2. Never just give the final answer. Guide the student with hints and questions.
3. Use the Socratic method: break the problem into small steps and ask one guiding question at a time.
4. Be encouraging and concise (under 150 words per reply).
5. If the student is stuck after two hints, show a small worked step, then ask them to continue.
6. Do not invent facts. If you are unsure, say so.
7. Stay on the student's topic; politely redirect off-topic requests."""


def _format_history(request: TutorRequest) -> str:
    if not request.history:
        return "(no previous messages)"
    lines = []
    for message in request.history[-10:]:
        speaker = "Student" if message.role == "user" else "Tutor"
        lines.append(f"{speaker}: {message.content}")
    return "\n".join(lines)


def _build_user_prompt(request: TutorRequest) -> str:
    parts = [
        f"TOPIC: {request.topic}",
        f"CONVERSATION SO FAR:\n{_format_history(request)}",
        f"STUDENT QUESTION: {request.question}",
    ]
    if request.language:
        parts.append(f"Preferred language: {request.language}")
    return "\n\n".join(parts)


async def stream_tutor(request: TutorRequest) -> AsyncIterator[str]:
    # SSE: kirim potongan teks tutor secara real-time, lalu [DONE].
    logger.info(
        "Tutor request: topic=%r question_chars=%d history=%d",
        request.topic,
        len(request.question),
        len(request.history),
    )

    async for chunk in llm.chat_completion_stream(
        _build_user_prompt(request),
        system=SYSTEM_PROMPT,
        temperature=0.6,
        max_tokens=TUTOR_MAX_TOKENS,
        reasoning_effort="low",
        thinking=False,
    ):
        # Frame JSON agar aman terhadap newline di dalam chunk.
        yield f"data: {json.dumps({'type': 'delta', 'content': chunk})}\n\n"

    yield "data: [DONE]\n\n"


# --- Quiz dari jadwal (mode quiz_from_schedule) ---

QUIZ_SYSTEM_PROMPT = """You are Study Agent Quiz Maker. Create exactly 3 multiple-choice questions about the given topic.

RULES:
1. Each question has exactly 4 options.
2. Exactly one option is correct; correct_index is 0-based.
3. Provide a short explanation for the correct answer.
4. Test understanding, not trivia.
5. Use the same language as the topic if it is clearly non-English; otherwise English.
6. Output JSON only, matching: {"questions":[{"question":"...","options":["A","B","C","D"],"correct_index":0,"explanation":"..."}]}"""


class _LLMQuizOutput(BaseModel):
    questions: list[QuizQuestion]


def _find_session_topic(plan_data: dict, week_number: int, day_name: str) -> str | None:
    # Cari topik sesi berdasarkan minggu & nama hari di weekly_schedule.
    normalized = day_name.strip().lower()
    for week in plan_data.get("weekly_schedule", []):
        if week.get("week") != week_number:
            continue
        for day in week.get("days", []):
            if str(day.get("day", "")).strip().lower() == normalized:
                return day.get("topic")
    return None


async def generate_quiz(
    user_id: uuid.UUID,
    plan_id: uuid.UUID,
    week_number: int,
    day_name: str,
) -> QuizResponse:
    # Ambil topik dari jadwal, lalu minta LLM membuat 3 soal pilihan ganda.
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
        plan_data = plan.plan_data or {}

    topic = _find_session_topic(plan_data, week_number, day_name)
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found in this plan's schedule.",
        )

    logger.info(
        "Quiz request: plan_id=%s week=%d day=%s topic=%r",
        plan_id,
        week_number,
        day_name,
        topic,
    )

    response = await llm.chat_completion_json(
        f"TOPIC: {topic}\nCreate 3 multiple-choice questions for this study session.",
        system=QUIZ_SYSTEM_PROMPT,
        schema=_LLMQuizOutput,
        temperature=0.5,
        max_tokens=QUIZ_MAX_TOKENS,
        reasoning_effort="low",
        thinking=False,
    )
    output = _LLMQuizOutput.model_validate(response.data)
    questions = [
        question
        for question in output.questions
        if 0 <= question.correct_index < len(question.options)
    ][:3]
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Quiz generation returned no valid questions.",
        )
    return QuizResponse(topic=topic, questions=questions)
