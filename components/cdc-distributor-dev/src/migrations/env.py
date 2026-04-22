import asyncio
import os
import re
from io import StringIO
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy.ext.asyncio.engine import create_async_engine
from sqlalchemy.future import Connection

from src.core.config import settings
from src.core.db.base import Base
from src.core.db.models import BortStreamOffset  # noqa: F401 — register model

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_database_url() -> str:
    override_url = config.get_main_option("sqlalchemy.url")
    if override_url:
        return override_url
    url = settings.distributor.POSTGRES_URL
    if url is None:
        raise RuntimeError("DISTRIBUTOR__POSTGRES_HOST is required")
    return url.replace("postgresql://", "postgresql+asyncpg://", 1)


_REVISION_NUMBER_RE = re.compile(r"^(\d{3})_")


def _next_numeric_revision(existing: list[int]) -> str:
    last = max(existing) if existing else 0
    return f"{last + 1:03d}"


def _ensure_numeric_revision(context_obj, revision, directives) -> None:  # type: ignore[no-untyped-def]
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


def _current_command_name() -> str | None:
    cmd_opts = getattr(config, "cmd_opts", None)
    if cmd_opts is None:
        return None
    cmd = getattr(cmd_opts, "cmd", None)
    if not cmd:
        return None
    command_fn = cmd[0]
    return getattr(command_fn, "__name__", None)


def _should_run_offline_revision() -> bool:
    cmd_opts = getattr(config, "cmd_opts", None)
    if cmd_opts is None:
        return False
    return _current_command_name() == "revision" and not getattr(
        cmd_opts, "autogenerate", False,
    )


def run_migrations_offline() -> None:
    context.configure(
        url=_get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        process_revision_directives=_ensure_numeric_revision,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_revision_offline() -> None:
    output_buffer = StringIO()
    context.configure(
        dialect_name="postgresql",
        target_metadata=target_metadata,
        as_sql=True,
        output_buffer=output_buffer,
        process_revision_directives=_ensure_numeric_revision,
    )

    context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        process_revision_directives=_ensure_numeric_revision,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(_get_database_url())

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


if _should_run_offline_revision():
    run_revision_offline()
elif context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
