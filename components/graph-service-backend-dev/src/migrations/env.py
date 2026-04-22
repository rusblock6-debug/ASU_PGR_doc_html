import os
import re
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.models.database import Base
from config.settings import get_settings

settings = get_settings()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# --- Numeric revision naming (001, 002, ...) ---

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


def _include_object(object, name, type_, reflected, compare_to):
    """Exclude PostGIS system tables from autogenerate."""
    if type_ == "table" and name in ("spatial_ref_sys",):
        return False
    return True

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


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
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_object=_include_object,
        process_revision_directives=_ensure_numeric_revision,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.database_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # PostGIS расширение уже установлено через init.sql
        # НЕ создаем здесь чтобы не откатывать транзакцию миграции

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_object=_include_object,
            process_revision_directives=_ensure_numeric_revision,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
