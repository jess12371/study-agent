# SQLAlchemy engine + session factory untuk koneksi ke PostgreSQL (Supabase).

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Engine sinkron (psycopg2). pool_pre_ping menghindari koneksi mati (umum di Supabase).
# pool_recycle membuang koneksi yang sudah lama menganggur sebelum dipakai lagi.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    future=True,
)

# Factory session — autocommit/autoflush dimatikan agar eksplisit.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    # Dependency FastAPI: buka session per request, tutup otomatis setelah selesai.
    db = SessionLocal()
    try:
        yield db
    finally:
        try:
            db.close()
        except Exception:  # noqa: BLE001 - koneksi bisa putus (mis. Supabase) saat request panjang
            db.invalidate()
