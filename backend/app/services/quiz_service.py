# Service gamifikasi quiz — simpan skor & ambil riwayat.

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.quiz_attempt import QuizAttempt
from app.models.study_plan import StudyPlan
from app.schemas.quiz import (
    QuizAttemptResponse,
    QuizHistoryResponse,
    QuizSubmitRequest,
)

logger = logging.getLogger(__name__)


def submit_quiz(
    db: Session, user_id: uuid.UUID, data: QuizSubmitRequest
) -> QuizAttempt:
    # Validasi plan milik user, lalu simpan percobaan quiz.
    plan = db.scalar(
        select(StudyPlan).where(
            StudyPlan.id == data.plan_id, StudyPlan.user_id == user_id
        )
    )
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found."
        )

    attempt = QuizAttempt(
        user_id=user_id,
        plan_id=data.plan_id,
        week_number=data.week_number,
        day_name=data.day_name,
        score=data.score,
        total_questions=data.total_questions,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    logger.info(
        "Quiz attempt disimpan: user_id=%s plan_id=%s score=%d/%d",
        user_id,
        data.plan_id,
        data.score,
        data.total_questions,
    )
    return attempt


def get_history(db: Session, user_id: uuid.UUID) -> QuizHistoryResponse:
    # Ambil semua attempt + topik goal, lalu hitung agregat.
    rows = db.execute(
        select(QuizAttempt, Goal.topic)
        .join(StudyPlan, QuizAttempt.plan_id == StudyPlan.id)
        .join(Goal, StudyPlan.goal_id == Goal.id)
        .where(QuizAttempt.user_id == user_id)
        .order_by(QuizAttempt.created_at.desc())
    ).all()

    attempts = [
        QuizAttemptResponse(
            id=attempt.id,
            plan_id=attempt.plan_id,
            week_number=attempt.week_number,
            day_name=attempt.day_name,
            score=attempt.score,
            total_questions=attempt.total_questions,
            created_at=attempt.created_at,
            goal_topic=topic,
        )
        for attempt, topic in rows
    ]

    percentages = [
        (attempt.score / attempt.total_questions * 100)
        for attempt in attempts
        if attempt.total_questions
    ]
    total = len(attempts)
    average = round(sum(percentages) / total, 1) if total else 0.0
    best = round(max(percentages), 1) if percentages else 0.0

    return QuizHistoryResponse(
        attempts=attempts,
        total_quizzes=total,
        average_score=average,
        best_score=best,
    )
