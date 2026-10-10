# Service goals (F-01) — CRUD goal dengan ownership check.

import logging
import uuid
from datetime import time

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.schemas.goal import GoalCreate, GoalUpdate

logger = logging.getLogger(__name__)


def _parse_time(value: str | None) -> time | None:
    # Konversi "HH:MM" → datetime.time.
    return None if value is None else time.fromisoformat(value)


def _not_found() -> HTTPException:
    # 404 (bukan 403) agar keberadaan goal user lain tidak bocor.
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")


def _get_owned_goal(db: Session, user_id: uuid.UUID, goal_id: uuid.UUID) -> Goal:
    # Ambil goal milik user; kalau bukan miliknya → 404.
    goal = db.scalar(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id)
    )
    if goal is None:
        raise _not_found()
    return goal


def create_goal(db: Session, user_id: uuid.UUID, data: GoalCreate) -> Goal:
    # Buat goal baru milik user.
    goal = Goal(
        user_id=user_id,
        topic=data.topic,
        current_level=data.current_level,
        target=data.target,
        deadline_months=data.deadline_months,
        work_hours_start=_parse_time(data.work_hours_start),
        work_hours_end=_parse_time(data.work_hours_end),
        work_days=data.work_days,
        preferred_study_time=data.preferred_study_time,
        max_session_minutes=data.max_session_minutes,
        unavailable_days=data.unavailable_days,
        status="active",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    logger.info("Goal dibuat: id=%s user_id=%s", goal.id, user_id)
    return goal


def list_goals(
    db: Session, user_id: uuid.UUID, status_filter: str | None = None
) -> list[Goal]:
    # Daftar goal milik user, opsional filter status.
    stmt = select(Goal).where(Goal.user_id == user_id).order_by(Goal.created_at.desc())
    if status_filter:
        stmt = stmt.where(Goal.status == status_filter)
    return list(db.scalars(stmt).all())


def get_goal(db: Session, user_id: uuid.UUID, goal_id: uuid.UUID) -> Goal:
    # Ambil satu goal milik user (404 kalau bukan miliknya).
    return _get_owned_goal(db, user_id, goal_id)


def update_goal(
    db: Session, user_id: uuid.UUID, goal_id: uuid.UUID, data: GoalUpdate
) -> Goal:
    # Update field yang dikirim saja.
    goal = _get_owned_goal(db, user_id, goal_id)
    updates = data.model_dump(exclude_unset=True)
    if "work_hours_start" in updates:
        updates["work_hours_start"] = _parse_time(updates["work_hours_start"])
    if "work_hours_end" in updates:
        updates["work_hours_end"] = _parse_time(updates["work_hours_end"])
    for field, value in updates.items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    logger.info("Goal diupdate: id=%s fields=%s", goal.id, sorted(updates.keys()))
    return goal


def delete_goal(db: Session, user_id: uuid.UUID, goal_id: uuid.UUID) -> None:
    # Hapus goal milik user (404 kalau bukan miliknya).
    goal = _get_owned_goal(db, user_id, goal_id)
    db.delete(goal)
    db.commit()
    logger.info("Goal dihapus: id=%s", goal_id)
