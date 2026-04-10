"""Tests for audit_lib.table — create_audit_table / create_audit_table_async."""

from __future__ import annotations

from collections.abc import AsyncIterator, Generator

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

import audit_lib
from tests.conftest import PG_ASYNC_URL, PG_SYNC_URL


@pytest.fixture
def sync_engine() -> Generator[sa.Engine]:
    engine = sa.create_engine(PG_SYNC_URL)
    with engine.begin() as conn:
        conn.execute(sa.text("DROP TABLE IF EXISTS audit_outbox CASCADE"))
    yield engine
    with engine.begin() as conn:
        conn.execute(sa.text("DROP TABLE IF EXISTS audit_outbox CASCADE"))
    engine.dispose()


@pytest.fixture
async def async_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(PG_ASYNC_URL)
    async with engine.begin() as conn:
        await conn.execute(sa.text("DROP TABLE IF EXISTS audit_outbox CASCADE"))
    yield engine
    async with engine.begin() as conn:
        await conn.execute(sa.text("DROP TABLE IF EXISTS audit_outbox CASCADE"))
    await engine.dispose()


def test_create_audit_table_creates_table(sync_engine: sa.Engine) -> None:
    """create_audit_table on an empty DB creates audit_outbox with indexes."""
    audit_lib.create_audit_table(sync_engine)

    insp = sa.inspect(sync_engine)
    assert "audit_outbox" in insp.get_table_names()

    indexes = insp.get_indexes("audit_outbox")
    index_names = {idx["name"] for idx in indexes}
    assert "ix_audit_outbox_entity" in index_names
    assert "ix_audit_outbox_processed" in index_names
    assert "ix_audit_outbox_timestamp" in index_names


def test_create_audit_table_idempotent(sync_engine: sa.Engine) -> None:
    """Calling create_audit_table twice is a no-op (no error)."""
    audit_lib.create_audit_table(sync_engine)
    audit_lib.create_audit_table(sync_engine)

    insp = sa.inspect(sync_engine)
    assert "audit_outbox" in insp.get_table_names()


def test_create_audit_table_invalid_engine() -> None:
    """Passing a non-Engine raises TypeError with a clear message."""
    with pytest.raises(TypeError, match="Expected a sqlalchemy.Engine"):
        audit_lib.create_audit_table("not-an-engine")  # type: ignore[arg-type]


def test_create_audit_table_invalid_async_engine_rejected(
    async_engine: AsyncEngine,
) -> None:
    """Passing an AsyncEngine to the sync variant raises TypeError."""
    with pytest.raises(TypeError, match="Expected a sqlalchemy.Engine"):
        audit_lib.create_audit_table(async_engine)  # type: ignore[arg-type]


async def test_create_audit_table_async_creates_table(
    async_engine: AsyncEngine,
) -> None:
    """create_audit_table_async on an empty DB creates audit_outbox."""
    await audit_lib.create_audit_table_async(async_engine)

    async with async_engine.connect() as conn:
        result = await conn.run_sync(
            lambda sync_conn: sa.inspect(sync_conn).get_table_names()
        )
    assert "audit_outbox" in result


async def test_create_audit_table_async_idempotent(
    async_engine: AsyncEngine,
) -> None:
    """Calling create_audit_table_async twice is a no-op."""
    await audit_lib.create_audit_table_async(async_engine)
    await audit_lib.create_audit_table_async(async_engine)

    async with async_engine.connect() as conn:
        result = await conn.run_sync(
            lambda sync_conn: sa.inspect(sync_conn).get_table_names()
        )
    assert "audit_outbox" in result


async def test_create_audit_table_async_invalid_engine() -> None:
    """Passing a non-AsyncEngine raises TypeError."""
    expected = "Expected a sqlalchemy.ext.asyncio.AsyncEngine"
    with pytest.raises(TypeError, match=expected):
        await audit_lib.create_audit_table_async("not-an-engine")


async def test_create_audit_table_async_sync_engine_rejected(
    sync_engine: sa.Engine,
) -> None:
    """Passing a sync Engine to the async variant raises TypeError."""
    expected = "Expected a sqlalchemy.ext.asyncio.AsyncEngine"
    with pytest.raises(TypeError, match=expected):
        await audit_lib.create_audit_table_async(sync_engine)
