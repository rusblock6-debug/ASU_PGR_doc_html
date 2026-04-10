import alembic_postgresql_enum
import asyncio
import os
import re
from io import StringIO
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy.ext.asyncio.engine import create_async_engine
from sqlalchemy.future import Connection

from src.app.model import load_all_models
# NOTE: app config is still used as a fallback when Alembic isn't provided an explicit URL.
from src.core.config import get_settings
from src.core.database.postgres.meta import meta

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
app_config = get_settings()
alembic_postgresql_enum
config = context.config

load_all_models()
# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = meta


def _get_database_url() -> str:
    override_url = config.get_main_option("sqlalchemy.url")
    if override_url:
        return override_url
    return str(app_config.POSTGRES_URL)


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


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def _current_command_name() -> str | None:
    """Return the alembic CLI command name, if available."""
    cmd_opts = getattr(config, "cmd_opts", None)
    if cmd_opts is None:
        return None
    cmd = getattr(cmd_opts, "cmd", None)
    if not cmd:
        return None
    command_fn = cmd[0]
    return getattr(command_fn, "__name__", None)


def _should_run_offline_revision() -> bool:
    """Return True if we generate a revision without autogenerate."""
    cmd_opts = getattr(config, "cmd_opts", None)
    if cmd_opts is None:
        return False
    return _current_command_name() == "revision" and not getattr(
        cmd_opts, "autogenerate", False,
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
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
    """Create a revision without opening a DB connection."""
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
    """Run actual sync migrations.

    Args:
        connection: connection to the database.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        process_revision_directives=_ensure_numeric_revision,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = create_async_engine(_get_database_url())

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


if _should_run_offline_revision():
    run_revision_offline()
elif context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
