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

from src.core.config import get_settings

from .fixture import *

settings = get_settings()


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, Any]:
    try:
        container = PostgresContainer("postgres:16")
    except DockerException as exc:
        pytest.skip(f"Docker unavailable for integration tests: {exc}")

    with container as pg:
        yield pg


@pytest_asyncio.fixture(loop_scope="session")
async def async_engine(postgres_container) -> AsyncGenerator[AsyncEngine, Any]:
    async_url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
    engine = create_async_engine(
        async_url,
        echo=False,
    )
    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def async_session(
    async_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession | Any, Any]:
    async_session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_factory() as session:
        yield session


@pytest.fixture(scope="session")
def alembic_config(postgres_container) -> Config:
    sync_url = postgres_container.get_connection_url()
    async_url = sync_url.replace("psycopg2", "asyncpg")
    project_root = Path(__file__).resolve().parents[2]
    cfg = Config(str(project_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(project_root / "src/migrations"))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture(scope="session", autouse=True)
def apply_migrations(alembic_config: Config):
    command.upgrade(alembic_config, "head")


@pytest.fixture(scope="session")
def trip_id() -> str:
    return "47d40025"
