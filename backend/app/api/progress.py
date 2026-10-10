# Endpoint API untuk fitur F-04 — Progress Tracker (butuh auth).

import logging
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.progress import ProgressEntry, ProgressMark, ProgressStats
from app.services import progress_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plans", tags=["progress"])


@router.patch("/{plan_id}/progress", response_model=ProgressEntry)
async def mark_progress(
    plan_id: uuid.UUID,
    payload: ProgressMark,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgressEntry:
    # Tandai/ubah status satu sesi (upsert).
    logger.info("PATCH /api/plans/%s/progress user_id=%s", plan_id, current_user.id)
    return progress_service.mark_progress(db, current_user.id, plan_id, payload)


@router.get("/{plan_id}/progress", response_model=list[ProgressEntry])
async def list_progress(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProgressEntry]:
    # Daftar semua entry progres plan.
    return progress_service.get_progress(db, current_user.id, plan_id)


@router.get("/{plan_id}/progress/stats", response_model=ProgressStats)
async def progress_stats(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgressStats:
    # Statistik progres plan.
    return progress_service.get_stats(db, current_user.id, plan_id)


@router.post("/{plan_id}/progress/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_progress(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    # Reset seluruh progres plan.
    progress_service.reset_progress(db, current_user.id, plan_id)
