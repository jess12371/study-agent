# Service F-04 — Progress Tracker.
# Upsert progres per sesi, hitung completion rate, total jam, dan streak.

import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.progress_entry import ProgressEntry as ProgressEntryModel
from app.models.study_plan import StudyPlan
from app.schemas.progress import ProgressMark, ProgressStats

logger = logging.getLogger(__name__)


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")


def _get_owned_plan(db: Session, user_id: uuid.UUID, plan_id: uuid.UUID) -> StudyPlan:
    # Ambil plan milik user; 404 kalau tidak ada / bukan miliknya.
    plan = db.scalar(
        select(StudyPlan).where(StudyPlan.id == plan_id, StudyPlan.user_id == user_id)
    )
    if plan is None:
        raise _not_found()
    return plan


def mark_progress(
    db: Session,
    user_id: uuid.UUID,
    plan_id: uuid.UUID,
    data: ProgressMark,
) -> ProgressEntryModel:
    # Upsert entry progres untuk satu sesi.
    _get_owned_plan(db, user_id, plan_id)

    entry = db.scalar(
        select(ProgressEntryModel).where(
            ProgressEntryModel.plan_id == plan_id,
            ProgressEntryModel.week_number == data.week_number,
            ProgressEntryModel.day_name == data.day_name,
            ProgressEntryModel.session_index == data.session_index,
        )
    )
    if entry is None:
        entry = ProgressEntryModel(
            plan_id=plan_id,
            week_number=data.week_number,
            day_name=data.day_name,
            session_index=data.session_index,
        )
        db.add(entry)

    entry.status = data.status
    entry.actual_duration = data.actual_duration
    entry.difficulty_rating = data.difficulty_rating
    entry.notes = data.notes
    if data.scheduled_at is not None:
        entry.scheduled_at = data.scheduled_at

    # Kelola completed_at sesuai status.
    if data.status == "completed":
        entry.completed_at = entry.completed_at or datetime.now(timezone.utc)
    else:
        entry.completed_at = None

    db.commit()
    db.refresh(entry)
    logger.info(
        "Progress ditandai: plan_id=%s week=%s day=%s idx=%s status=%s",
        plan_id,
        data.week_number,
        data.day_name,
        data.session_index,
        data.status,
    )
    return entry


def get_progress(
    db: Session, user_id: uuid.UUID, plan_id: uuid.UUID
) -> list[ProgressEntryModel]:
    # Daftar entry progres milik plan user.
    _get_owned_plan(db, user_id, plan_id)
    stmt = (
        select(ProgressEntryModel)
        .where(ProgressEntryModel.plan_id == plan_id)
        .order_by(
            ProgressEntryModel.week_number,
            ProgressEntryModel.session_index,
        )
    )
    return list(db.scalars(stmt).all())


def _plan_sessions(plan: StudyPlan) -> list[dict]:
    # Susun daftar sesi terurut dari plan_data (semua minggu yang dijadwalkan).
    sessions: list[dict] = []
    data = plan.plan_data or {}
    for week in data.get("weekly_schedule", []):
        week_number = week.get("week")
        for index, day in enumerate(week.get("days", [])):
            sessions.append(
                {
                    "week_number": week_number,
                    "day_name": day.get("day"),
                    "session_index": index,
                    "duration_minutes": day.get("duration_minutes") or 0,
                }
            )
    return sessions


def _longest_run(flags: list[bool]) -> int:
    # Panjang run True terpanjang.
    best = 0
    current = 0
    for flag in flags:
        current = current + 1 if flag else 0
        best = max(best, current)
    return best


def get_stats(db: Session, user_id: uuid.UUID, plan_id: uuid.UUID) -> ProgressStats:
    # Hitung statistik progres plan.
    plan = _get_owned_plan(db, user_id, plan_id)
    sessions = _plan_sessions(plan)

    entries = db.scalars(
        select(ProgressEntryModel).where(ProgressEntryModel.plan_id == plan_id)
    ).all()
    by_key = {
        (e.week_number, e.day_name, e.session_index): e for e in entries
    }

    statuses: list[str] = []
    completed_flags: list[bool] = []
    completed = 0
    skipped = 0
    total_minutes = 0

    for session in sessions:
        entry = by_key.get(
            (session["week_number"], session["day_name"], session["session_index"])
        )
        session_status = entry.status if entry else "pending"
        statuses.append(session_status)
        is_completed = session_status == "completed"
        completed_flags.append(is_completed)
        if is_completed:
            completed += 1
            minutes = entry.actual_duration if entry and entry.actual_duration else session["duration_minutes"]
            total_minutes += minutes or 0
        elif session_status == "skipped":
            skipped += 1

    total_sessions = len(sessions)
    # "pending" = belum selesai & belum di-skip (termasuk rescheduled).
    pending = total_sessions - completed - skipped

    # Streak: urutan sesi sesuai jadwal. Buang sesi terakhir yang masih pending,
    # lalu hitung run completed di ujung.
    trimmed = list(statuses)
    while trimmed and trimmed[-1] in ("pending", "rescheduled"):
        trimmed.pop()
    current_streak = 0
    for session_status in reversed(trimmed):
        if session_status == "completed":
            current_streak += 1
        else:
            break

    completion_rate = (completed / total_sessions) if total_sessions else 0.0

    return ProgressStats(
        completion_rate=round(completion_rate, 3),
        total_sessions=total_sessions,
        completed=completed,
        skipped=skipped,
        pending=pending,
        total_hours=round(total_minutes / 60, 2),
        current_streak=current_streak,
        longest_streak=_longest_run(completed_flags),
    )


def reset_progress(db: Session, user_id: uuid.UUID, plan_id: uuid.UUID) -> None:
    # Hapus semua entry progres untuk plan.
    _get_owned_plan(db, user_id, plan_id)
    db.query(ProgressEntryModel).filter(ProgressEntryModel.plan_id == plan_id).delete()
    db.commit()
    logger.info("Progress di-reset: plan_id=%s", plan_id)
