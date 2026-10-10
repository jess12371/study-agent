# Endpoint goals (F-01) — semua butuh autentikasi.

import logging
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.goal import GoalCreate, GoalResponse, GoalUpdate
from app.services import goal_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/goals", tags=["goals"])


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    payload: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalResponse:
    # Buat goal milik user yang login.
    logger.info("POST /api/goals user_id=%s", current_user.id)
    return goal_service.create_goal(db, current_user.id, payload)


@router.get("", response_model=list[GoalResponse])
async def list_goals(
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GoalResponse]:
    # Daftar goal milik user.
    return goal_service.list_goals(db, current_user.id, status_filter)


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalResponse:
    # Ambil satu goal (404 kalau bukan milik user).
    return goal_service.get_goal(db, current_user.id, goal_id)


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: uuid.UUID,
    payload: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalResponse:
    # Update goal milik user.
    return goal_service.update_goal(db, current_user.id, goal_id, payload)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    # Hapus goal milik user.
    goal_service.delete_goal(db, current_user.id, goal_id)
