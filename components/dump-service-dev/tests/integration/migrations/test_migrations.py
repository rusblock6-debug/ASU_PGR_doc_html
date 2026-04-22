import asyncio

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.database.postgres.base import Base


@pytest.mark.integration
async def test_alembic_head_matches_models(async_engine: AsyncEngine):
    async with async_engine.connect() as conn:
        diffs = await conn.run_sync(
            lambda sync_conn: compare_metadata(
                MigrationContext.configure(sync_conn),
                Base.metadata,
            ),
        )

    assert diffs == [], f"Schema differs from models, diffs:\n{diffs}"


@pytest.mark.integration
async def test_migrations_support_downgrade(
    async_engine: AsyncEngine,
    alembic_config: Config,
):
    try:
        await asyncio.to_thread(command.downgrade, alembic_config, "base")
    finally:
        await asyncio.to_thread(command.upgrade, alembic_config, "head")
