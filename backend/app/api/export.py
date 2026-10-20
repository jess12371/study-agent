# Endpoint API untuk fitur F-08 — Export plan (PDF & ICS), butuh auth.

import logging
import uuid

from fastapi import APIRouter, Depends, Response

from app.core.deps import get_current_user
from app.models.user import User
from app.services import export_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plans", tags=["export"])


@router.get("/{plan_id}/export/pdf")
async def export_plan_pdf(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
) -> Response:
    # Unduh study plan sebagai PDF.
    logger.info("GET /api/plans/%s/export/pdf user_id=%s", plan_id, current_user.id)
    data = export_service.export_plan_to_pdf(current_user.id, plan_id)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="study-plan-{plan_id}.pdf"'
        },
    )


@router.get("/{plan_id}/export/ics")
async def export_plan_ics(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
) -> Response:
    # Unduh study plan sebagai iCalendar (.ics) untuk Google/Apple/Outlook Calendar.
    logger.info("GET /api/plans/%s/export/ics user_id=%s", plan_id, current_user.id)
    data = export_service.export_plan_to_ics(current_user.id, plan_id)
    return Response(
        content=data,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="study-plan-{plan_id}.ics"'
        },
    )


@router.get("/{plan_id}/export-ics")
async def export_plan_ics_alias(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
) -> Response:
    # Alias endpoint sesuai spesifikasi: GET /api/plans/:id/export-ics.
    logger.info("GET /api/plans/%s/export-ics user_id=%s", plan_id, current_user.id)
    data = export_service.export_plan_to_ics(current_user.id, plan_id)
    return Response(
        content=data,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="study-plan-{plan_id}.ics"'
        },
    )
