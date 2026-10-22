# Endpoint API untuk fitur F-02 — Goal Feasibility Check.

import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.feasibility import (
    FeasibilityRequest,
    FeasibilityResponse,
    RescopeRequest,
    RescopeSuggestion,
)
from app.services.feasibility_service import check_feasibility, rescope_goal

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


@router.post("/rescope", response_model=RescopeSuggestion)
async def rescope_goal_analysis(payload: RescopeRequest) -> RescopeSuggestion:
    # Sarankan target & deadline baru agar goal menjadi realistis.
    logger.info("POST /api/feasibility/rescope topic=%r", payload.goal.topic)
    try:
        return await rescope_goal(payload)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Rescope gagal")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Re-scope failed due to an internal error.",
        ) from exc
