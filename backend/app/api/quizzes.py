# Endpoint API gamifikasi quiz (butuh auth).

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.quiz import (
    QuizAttemptResponse,
    QuizHistoryResponse,
    QuizSubmitRequest,
)
from app.services import quiz_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])


@router.post(
    "/submit", response_model=QuizAttemptResponse, status_code=status.HTTP_201_CREATED
)
async def submit_quiz_result(
    payload: QuizSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizAttemptResponse:
    # Simpan skor quiz setelah user selesai menjawab.
    logger.info(
        "POST /api/quizzes/submit user_id=%s plan_id=%s",
        current_user.id,
        payload.plan_id,
    )
    attempt = quiz_service.submit_quiz(db, current_user.id, payload)
    return QuizAttemptResponse.model_validate(attempt)


@router.get("/history", response_model=QuizHistoryResponse)
async def get_quiz_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizHistoryResponse:
    # Riwayat + statistik quiz user.
    return quiz_service.get_history(db, current_user.id)
