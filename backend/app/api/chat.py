# Endpoint API untuk fitur F-11 — Agent Dialog (chat), butuh auth.

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.chat import (
    ChatActionRequest,
    ChatActionResult,
    ChatHistoryResponse,
    ChatRequest,
)
from app.services import chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/goals", tags=["chat"])


@router.get("/{goal_id}/chat", response_model=ChatHistoryResponse)
async def get_chat_history(
    goal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
) -> ChatHistoryResponse:
    # Riwayat dialog untuk goal ini.
    return ChatHistoryResponse(messages=chat_service.get_history(current_user.id, goal_id))


@router.post("/{goal_id}/chat")
async def post_chat(
    goal_id: uuid.UUID,
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    # Kirim pesan ke agent (SSE stream).
    logger.info("POST /api/goals/%s/chat user_id=%s", goal_id, current_user.id)
    return StreamingResponse(
        chat_service.stream_message(current_user.id, goal_id, payload.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{goal_id}/chat/action", response_model=ChatActionResult)
async def run_chat_action(
    goal_id: uuid.UUID,
    payload: ChatActionRequest,
    current_user: User = Depends(get_current_user),
) -> ChatActionResult:
    # Eksekusi action button dari agent.
    logger.info("POST /api/goals/%s/chat/action type=%s", goal_id, payload.action_type)
    try:
        return await chat_service.execute_action(current_user.id, goal_id, payload)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chat action gagal")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Action failed due to an internal error.",
        ) from exc


@router.delete("/{goal_id}/chat", status_code=status.HTTP_204_NO_CONTENT)
async def clear_chat(
    goal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
) -> None:
    # Bersihkan riwayat dialog.
    chat_service.clear_history(current_user.id, goal_id)
