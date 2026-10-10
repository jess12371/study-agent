# Endpoint API untuk fitur F-05 — Adaptive Reschedule (butuh auth).

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.reschedule import (
    RescheduleAnalysis,
    RescheduleRequest,
    RescheduleResult,
)
from app.services import reschedule_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plans", tags=["reschedule"])


@router.get("/{plan_id}/reschedule/analyze", response_model=RescheduleAnalysis)
async def analyze_plan(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
) -> RescheduleAnalysis:
    # Analisis keterlambatan + 4 opsi adaptasi.
    logger.info("GET /api/plans/%s/reschedule/analyze user_id=%s", plan_id, current_user.id)
    try:
        return await reschedule_service.analyze_progress(current_user.id, plan_id)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Reschedule analyze gagal")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Reschedule analysis failed due to an internal error.",
        ) from exc


@router.post("/{plan_id}/reschedule/apply", response_model=RescheduleResult)
async def apply_plan_reschedule(
    plan_id: uuid.UUID,
    payload: RescheduleRequest,
    current_user: User = Depends(get_current_user),
) -> RescheduleResult:
    # Terapkan opsi adaptasi → buat plan versi baru.
    logger.info(
        "POST /api/plans/%s/reschedule/apply option=%s user_id=%s",
        plan_id,
        payload.option_type,
        current_user.id,
    )
    try:
        return await reschedule_service.apply_reschedule(current_user.id, plan_id, payload)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Reschedule apply gagal")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Reschedule failed due to an internal error.",
        ) from exc
