# Model `resources` — katalog materi belajar + embedding untuk semantic search.

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Dimensi embedding model all-MiniLM-L6-v2.
EMBEDDING_DIM = 384


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    topic: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    type: Mapped[str | None] = mapped_column(String(50))  # video / artikel / kursus / buku / tool
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    level: Mapped[str | None] = mapped_column(String(50))  # beginner / intermediate / advanced
    is_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Deskripsi singkat + skill yang dilatih (untuk ditampilkan & memperkaya embedding).
    description: Mapped[str | None] = mapped_column(Text)
    skills: Mapped[list[str] | None] = mapped_column(JSONB)
    # Embedding untuk pencarian mirip (pgvector), 384 dimensi (all-MiniLM-L6-v2).
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
