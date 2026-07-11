"""Updated Alembic env.py — imports all models for autogenerate."""

from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Alembic can detect them for autogenerate
from app.core.database import Base  # noqa: E402
import app.models.user  # noqa: E402, F401
import app.models.meeting  # noqa: E402, F401
import app.models.participant  # noqa: E402, F401
import app.models.message  # noqa: E402, F401
import app.models.recording  # noqa: E402, F401
import app.models.notification  # noqa: E402, F401
import app.models.invitation  # noqa: E402, F401
import app.models.meeting_settings  # noqa: E402, F401
import app.models.file  # noqa: E402, F401
import app.models.audit_log  # noqa: E402, F401

target_metadata = Base.metadata


def get_url() -> str:
    return os.getenv(
        "DATABASE_SYNC_URL",
        os.getenv(
            "DATABASE_URL",
            config.get_main_option("sqlalchemy.url", "postgresql://meetadmin:meetpassword@localhost:5432/enterprisemeet"),
        ).replace("+asyncpg", ""),  # Use sync driver for migrations
    )


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
