# Model `study_plans` — hasil generate plan (JSON) per goal.

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    goal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Output agent (milestone, jadwal mingguan, resource) dalam bentuk JSON.
    plan_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    # Versi plan — naik saat adaptive reschedule membuat plan baru.
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    # Alasan versi ini dibuat: initial / reschedule / regenerate.
    reason: Mapped[str] = mapped_column(
        String(30), nullable=False, default="initial", server_default=text("'initial'")
    )
    # Menunjuk ke plan versi berikutnya kalau plan ini sudah digantikan.
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("study_plans.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    goal: Mapped["Goal"] = relationship(back_populates="study_plans")
    user: Mapped["User"] = relationship(back_populates="study_plans")
    progress_entries: Mapped[list["ProgressEntry"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )
