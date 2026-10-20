# Endpoint API untuk fitur F-03 — Study Plan Generator (butuh auth).

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.plan import (
    PlanGenerateRequest,
    PlanRequest,
    PlanResponse,
    PlanVersion,
)
from app.services import goal_service
from app.services.feasibility_service import check_feasibility
from app.services.plan_service import (
    build_feasibility_request,
    generate_plan,
    generate_plan_stream,
    get_latest_plan_for_goal,
    get_plan,
    get_plan_by_goal_version,
    list_plan_versions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plans", tags=["plans"])


async def _prepare_request(
    payload: PlanGenerateRequest, user: User, db: Session
) -> tuple[PlanRequest, uuid.UUID]:
    # Ambil goal dari DB (verify ownership, 404 kalau bukan milik user) dan
    # siapkan PlanRequest. Feasibility dijalankan bila client tidak mengirimnya.
    goal = goal_service.get_goal(db, user.id, payload.goal_id)
    feasibility_request = build_feasibility_request(goal)
    feasibility_result = payload.feasibility_result or await check_feasibility(
        feasibility_request
    )
    request = PlanRequest(goal=feasibility_request, feasibility_result=feasibility_result)
    return request, goal.id


@router.post("/generate")
async def create_plan(
    payload: PlanGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    # Generate plan sebagai SSE stream: status → delta teks real-time → plan final.
    logger.info("POST /api/plans/generate user_id=%s goal_id=%s", current_user.id, payload.goal_id)
    try:
        request, goal_id = await _prepare_request(payload, current_user, db)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Generate plan gagal (prepare)")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Plan generation failed due to an internal error.",
        ) from exc
    return StreamingResponse(
        generate_plan_stream(request, user_id=current_user.id, goal_id=goal_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Cegah buffering oleh proxy (mis. Nginx).
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/generate/stream")
async def create_plan_stream(
    payload: PlanGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    # Generate plan dengan SSE stream. Ownership diverifikasi sebelum stream dibuka,
    # supaya error 404 bisa dikembalikan sebagai JSON biasa.
    logger.info("POST /api/plans/generate/stream user_id=%s goal_id=%s", current_user.id, payload.goal_id)
    request, goal_id = await _prepare_request(payload, current_user, db)
    return StreamingResponse(
        generate_plan_stream(request, user_id=current_user.id, goal_id=goal_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Cegah buffering oleh proxy (mis. Nginx).
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/by-goal/{goal_id}/history", response_model=list[PlanVersion])
async def read_plan_history(
    goal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
) -> list[PlanVersion]:
    # Semua versi plan untuk goal ini (Plan History).
    return list_plan_versions(current_user.id, goal_id)


@router.get("/by-goal/{goal_id}", response_model=PlanResponse)
async def read_plan_for_goal(
    goal_id: uuid.UUID,
    version: int | None = None,
    current_user: User = Depends(get_current_user),
) -> PlanResponse:
    # Plan versi tertentu, atau versi terbaru kalau `version` tidak diisi.
    if version is not None:
        plan = get_plan_by_goal_version(current_user.id, goal_id, version)
    else:
        plan = get_latest_plan_for_goal(current_user.id, goal_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No plan for this goal."
        )
    return plan


@router.get("/{plan_id}", response_model=PlanResponse)
async def read_plan(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
) -> PlanResponse:
    # Ambil detail plan milik user (404 kalau bukan miliknya).
    logger.info("GET /api/plans/%s user_id=%s", plan_id, current_user.id)
    plan = get_plan(plan_id, current_user.id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found."
        )
    return plan
