# Model `progress_entries` — catatan progres belajar per sesi/hari.

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProgressEntry(Base):
    __tablename__ = "progress_entries"
    # Satu entry per sesi (plan + minggu + hari + index sesi) → mendukung upsert.
    __table_args__ = (
        UniqueConstraint(
            "plan_id",
            "week_number",
            "day_name",
            "session_index",
            name="uq_progress_entry_session",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("study_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    week_number: Mapped[int | None] = mapped_column(Integer)
    day_name: Mapped[str | None] = mapped_column(String(20))
    # Index sesi dalam satu minggu (urutan hari pada plan).
    session_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Status: pending / completed / skipped / rescheduled.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # Durasi aktual belajar (menit).
    actual_duration: Mapped[int | None] = mapped_column(Integer)
    # Penilaian tingkat kesulitan sesi (1-5).
    difficulty_rating: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    plan: Mapped["StudyPlan"] = relationship(back_populates="progress_entries")
