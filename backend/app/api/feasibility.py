# Endpoint API untuk fitur F-02 — Goal Feasibility Check.

import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.feasibility import FeasibilityRequest, FeasibilityResponse
from app.services.feasibility_service import check_feasibility

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feasibility", tags=["feasibility"])


@router.post("/check", response_model=FeasibilityResponse)
async def check_goal_feasibility(payload: FeasibilityRequest) -> FeasibilityResponse:
    # Analisis kelayakan target belajar user.
    # Error body/invalid request ditangani global handler di main.py (→ 400).
    logger.info("POST /api/feasibility/check topic=%r", payload.topic)
    try:
        return await check_feasibility(payload)
    except Exception as exc:  # noqa: BLE001 - error LLM / guardrail → 500
        logger.exception("Feasibility check gagal (LLM error)")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Feasibility check failed due to an internal error.",
        ) from exc
