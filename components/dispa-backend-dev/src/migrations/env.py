"""
Alembic environment configuration.
"""
import asyncio
import os
import sys
from logging.config import fileConfig
import re
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Добавление корневой директории проекта в Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None
try:
    from app.database.base import Base
    target_metadata = Base.metadata
except ImportError:
    target_metadata = None

# compiled regex used to find already issued numeric revisions
_REVISION_NUMBER_RE = re.compile(r"^(\d{3})_")


def get_url():
    """
    Получение URL базы данных из переменных окружения
    """
    # Используем существующую конфигурацию приложения
    try:
        from app.core.config import settings
        # Используем async URL как есть
        return settings.database_url
    except ImportError:
        # Fallback на переменные окружения
        import os
        postgres_user = os.getenv("POSTGRES_USER", "postgres")
        postgres_password = os.getenv("POSTGRES_PASSWORD", "postgres")
        postgres_host = os.getenv("POSTGRES_HOST", "postgres")
        postgres_port = os.getenv("POSTGRES_PORT", "5432")
        postgres_db = os.getenv("POSTGRES_DB", "dispatching")
        return f"postgresql+asyncpg://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"


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

def do_run_migrations(connection: Connection) -> None:
    """Run migrations with given connection"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        process_revision_directives=_ensure_numeric_revision,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode with async engine.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode"""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
