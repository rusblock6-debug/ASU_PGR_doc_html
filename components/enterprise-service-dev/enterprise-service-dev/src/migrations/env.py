"""
Alembic environment configuration.
"""
import os
import re
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from app.database.base import Base
from app.core.config import settings

# Импортируем все модели, чтобы Alembic видел их метаданные
from app.database.models import (
    EnterpriseSettings,
    WorkRegime,
    Vehicle,
    Pdm,

    Shas,
    Status,
    LoadType,
    LoadTypeCategory,
)

config = context.config

# Преобразуем async URL в синхронный для миграций
# postgresql+asyncpg:// -> postgresql+psycopg2://
database_url = settings.DATABASE_URL
if database_url.startswith("postgresql+asyncpg://"):
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
elif database_url.startswith("postgresql://"):
    # Если уже синхронный URL, оставляем как есть
    pass

config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# compiled regex used to find already issued numeric revisions
_REVISION_NUMBER_RE = re.compile(r"^(\d{3})_")


def _next_numeric_revision(existing: list[int]) -> str:
    """Return the next sequential revision id as a zero-padded string."""
    last = max(existing) if existing else 0
    return f"{last + 1:03d}"


def _ensure_numeric_revision(context_obj, revision, directives) -> None:
    """Force Alembic to use 001/002/... revision ids and filenames."""
    if not directives:
        return

    script = directives[0]
    script_directory = getattr(context, "script", None)
    if script_directory is None:
        return

    versions_path = Path(script_directory.versions)
    versions_path.mkdir(parents=True, exist_ok=True)

    existing = []
    for filename in os.listdir(versions_path):
        match = _REVISION_NUMBER_RE.match(filename)
        if match:
            existing.append(int(match.group(1)))

    next_revision = _next_numeric_revision(existing)
    script.rev_id = next_revision

    slug = getattr(script, "slug", None)
    if not slug:
        message = getattr(getattr(config, "cmd_opts", None), "message", None)
        if message:
            slug = re.sub(r"\W+", "_", message.strip()).strip("_")
    slug = slug or "migration"

    script.path = str(versions_path / f"{next_revision}_{slug}.py")


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        process_revision_directives=_ensure_numeric_revision,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = database_url
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=_ensure_numeric_revision,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
