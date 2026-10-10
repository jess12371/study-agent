# Environment Alembic — menyambungkan metadata model ke database (online & offline).

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import Base + semua model agar terdaftar di metadata (dibutuhkan autogenerate).
from app.core.config import settings
from app.db.base import Base
from app.models import Goal, ProgressEntry, Resource, StudyPlan, User  # noqa: F401

# Objek konfigurasi Alembic (dari alembic.ini).
config = context.config

# Set URL database dari settings (backend/.env), bukan dari alembic.ini.
config.set_main_option("sqlalchemy.url", settings.database_url)

# Setup logging dari file config.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata target untuk autogenerate migration.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    # Mode offline: hasilkan SQL tanpa koneksi ke database.
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Mode online: konek ke database lalu jalankan migration.
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
