from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from docker.errors import DockerException
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from tests.config import get_settings

settings = get_settings()


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, Any]:
    try:
        container = PostgresContainer(
            image="postgis/postgis:16-3.4",
            username=settings.postgres_user,
            port=settings.postgres_port,
            password=settings.postgres_password,  # noqa: S106
            dbname=settings.postgres_db,
        )
    except DockerException as exc:
        pytest.skip(f"Docker unavailable for integration tests: {exc}")

    with container as pg:
        yield pg


@pytest.fixture(scope="session")
def alembic_config(postgres_container: PostgresContainer) -> Config:
    sync_url = postgres_container.get_connection_url()
    async_url = sync_url.replace("psycopg2", "asyncpg")

    project_root = Path(__file__).resolve().parents[2]
    cfg = Config(str(project_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(project_root / "src/migrations"))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture(scope="session", autouse=True)
def apply_migrations(postgres_container: PostgresContainer, alembic_config: Config) -> None:
    sync_url = postgres_container.get_connection_url()

    from sqlalchemy import create_engine, text

    engine = create_engine(sync_url)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()
    engine.dispose()

    import config.settings as _settings_mod

    _settings_mod.get_settings = get_settings

    settings.postgres_host = postgres_container.get_container_host_ip()
    settings.postgres_port = int(postgres_container.get_exposed_port(5432))

    command.upgrade(alembic_config, "head")


@pytest_asyncio.fixture(loop_scope="session")
async def async_engine(postgres_container: PostgresContainer) -> AsyncGenerator[AsyncEngine, Any]:
    async_url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
    engine = create_async_engine(async_url, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def async_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, Any]:
    session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
