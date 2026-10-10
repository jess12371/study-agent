# Base declarative SQLAlchemy 2.0 — parent class untuk semua model.

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    # Semua model di app/models mewarisi Base ini.
    # Metadata-nya dipakai Alembic untuk autogenerate migration.
    pass
