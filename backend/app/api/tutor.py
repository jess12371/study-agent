# Endpoint API Socratic Tutor (streaming) + Quiz dari jadwal.

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.deps import get_current_user_optional
from app.models.user import User
from app.schemas.tutor import TutorRequest
from app.services import tutor_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tutor", tags=["tutor"])


@router.post("/chat")
async def tutor_chat(
    payload: TutorRequest,
    current_user: User | None = Depends(get_current_user_optional),
):
    # Mode quiz: butuh auth + plan milik user; mengembalikan JSON.
    if payload.mode == "quiz_from_schedule":
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for quiz mode.",
            )
        return await tutor_service.generate_quiz(
            current_user.id,
            payload.plan_id,  # type: ignore[arg-type]
            payload.week_number,  # type: ignore[arg-type]
            payload.day_name,  # type: ignore[arg-type]
        )

    # Mode chat: streaming SSE (boleh anonim).
    logger.info("POST /api/tutor/chat topic=%r", payload.topic)
    return StreamingResponse(
        tutor_service.stream_tutor(payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
