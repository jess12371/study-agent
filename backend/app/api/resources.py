# Endpoint API untuk fitur F-06 — Resource Recommendation.

import logging
import uuid

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.resource import ResourceResponse
from app.services import resource_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["resources"])


@router.get("/api/resources/search", response_model=list[ResourceResponse])
async def search_resources(
    q: str = Query(default="", description="Search query"),
    topic: str | None = Query(default=None),
    level: str | None = Query(default=None),
    top_k: int = Query(default=10, ge=1, le=50),
    min_similarity: float | None = Query(default=None, ge=0.0, le=1.0),
) -> list[ResourceResponse]:
    # Semantic search resource (publik). Boost topic match bila `topic` diisi.
    return resource_service.search_resources(
        query=q,
        topic=topic,
        level=level,
        top_k=top_k,
        min_similarity=min_similarity,
        prefer_topic=topic,
    )


@router.get("/api/plans/{plan_id}/resources/recommend", response_model=list[ResourceResponse])
async def recommend_resources(
    plan_id: uuid.UUID,
    top_k: int = Query(default=8, ge=1, le=50),
    current_user: User = Depends(get_current_user),
) -> list[ResourceResponse]:
    # Rekomendasi resource untuk sebuah plan (butuh auth).
    logger.info("GET /api/plans/%s/resources/recommend user_id=%s", plan_id, current_user.id)
    return resource_service.recommend_for_plan(current_user.id, plan_id, top_k=top_k)
