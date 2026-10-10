# Model `goals` — tujuan belajar + preferensi jadwal user.

import uuid
from datetime import datetime, time
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Time, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    current_level: Mapped[str | None] = mapped_column(String(100))
    target: Mapped[str | None] = mapped_column(String(300))
    deadline_months: Mapped[int | None] = mapped_column(Integer)
    # Jam kerja user, mis. 09:00 dan 18:00.
    work_hours_start: Mapped[time | None] = mapped_column(Time)
    work_hours_end: Mapped[time | None] = mapped_column(Time)
    # Daftar hari kerja, mis. ["monday", "tuesday", ...].
    work_days: Mapped[list[str] | None] = mapped_column(JSONB)
    preferred_study_time: Mapped[str | None] = mapped_column(String(50))
    max_session_minutes: Mapped[int | None] = mapped_column(Integer)
    # Hari yang tidak bisa dipakai belajar.
    unavailable_days: Mapped[list[str] | None] = mapped_column(JSONB)
    # Status goal: active / archived / completed.
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default=text("'active'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="goals")
    study_plans: Mapped[list["StudyPlan"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan"
    )
