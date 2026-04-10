"""Integration tests for OutboxReader (US-002)."""

from __future__ import annotations

import datetime
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from audit_lib.daemon.reader import OutboxReader
from audit_lib.models import create_audit_model
from tests.conftest import PG_ASYNC_URL


class Base(DeclarativeBase):
    pass


AuditOutbox = create_audit_model(Base)


@pytest.fixture()
async def async_engine() -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(PG_ASYNC_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
def session_factory(
    async_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(async_engine, expire_on_commit=False)


async def _insert_outbox_record(
    session: AsyncSession,
    *,
    processed: bool = False,
    entity_type: str = "test_entity",
    operation: str = "create",
    timestamp: datetime.datetime | None = None,
) -> Any:
    """Insert a test outbox record and return it."""
    record = AuditOutbox(
        id=uuid.uuid4(),
        entity_type=entity_type,
        entity_id=str(uuid.uuid4()),
        operation=operation,
        old_values=None,
        new_values={"key": "value"},
        user_id="test-user",
        timestamp=timestamp or datetime.datetime.now(datetime.UTC),
        processed=processed,
        service_name="test-service",
    )
    session.add(record)
    await session.flush()
    return record


async def test_fetch_batch_returns_only_unprocessed(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    reader = OutboxReader(session_factory, batch_size=10)

    async with session_factory() as session:
        async with session.begin():
            rec_unprocessed = await _insert_outbox_record(
                session, processed=False
            )
            await _insert_outbox_record(session, processed=True)

    async with session_factory() as session:
        async with session.begin():
            batch = await reader.fetch_batch(session, outbox_model=AuditOutbox)

    assert len(batch) == 1
    assert batch[0].id == rec_unprocessed.id


async def test_fetch_batch_respects_batch_size(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    reader = OutboxReader(session_factory, batch_size=2)

    async with session_factory() as session:
        async with session.begin():
            for _ in range(5):
                await _insert_outbox_record(session, processed=False)

    async with session_factory() as session:
        async with session.begin():
            batch = await reader.fetch_batch(session, outbox_model=AuditOutbox)

    assert len(batch) == 2


async def test_fetch_batch_orders_by_timestamp(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    reader = OutboxReader(session_factory, batch_size=10)

    async with session_factory() as session:
        async with session.begin():
            ts_old = datetime.datetime(
                2020, 1, 1, tzinfo=datetime.UTC
            )
            ts_new = datetime.datetime(
                2025, 1, 1, tzinfo=datetime.UTC
            )
            rec_new = await _insert_outbox_record(
                session, processed=False, timestamp=ts_new
            )
            rec_old = await _insert_outbox_record(
                session, processed=False, timestamp=ts_old
            )

    async with session_factory() as session:
        async with session.begin():
            batch = await reader.fetch_batch(session, outbox_model=AuditOutbox)

    assert len(batch) == 2
    assert batch[0].id == rec_old.id
    assert batch[1].id == rec_new.id


async def test_mark_processed_then_fetch_returns_empty(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    reader = OutboxReader(session_factory, batch_size=10)

    async with session_factory() as session:
        async with session.begin():
            await _insert_outbox_record(session, processed=False)

    # Fetch → mark processed
    async with session_factory() as session:
        async with session.begin():
            batch = await reader.fetch_batch(session, outbox_model=AuditOutbox)
            assert len(batch) == 1
            await reader.mark_processed(
                session, [batch[0].id], outbox_model=AuditOutbox
            )

    # Subsequent fetch should return nothing
    async with session_factory() as session:
        async with session.begin():
            batch = await reader.fetch_batch(session, outbox_model=AuditOutbox)

    assert len(batch) == 0


async def test_mark_processed_with_empty_ids_is_noop(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    reader = OutboxReader(session_factory, batch_size=10)

    async with session_factory() as session:
        async with session.begin():
            await reader.mark_processed(
                session, [], outbox_model=AuditOutbox
            )


async def test_fetch_batch_returns_empty_when_no_records(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    reader = OutboxReader(session_factory, batch_size=10)

    async with session_factory() as session:
        async with session.begin():
            batch = await reader.fetch_batch(session, outbox_model=AuditOutbox)

    assert batch == []


async def test_full_cycle_insert_fetch_mark_refetch(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Full cycle: insert → fetch → mark processed → refetch empty."""
    reader = OutboxReader(session_factory, batch_size=100)

    # Insert 3 unprocessed records
    async with session_factory() as session:
        async with session.begin():
            recs = []
            for _ in range(3):
                r = await _insert_outbox_record(session, processed=False)
                recs.append(r)

    # Fetch all 3
    async with session_factory() as session:
        async with session.begin():
            batch = await reader.fetch_batch(session, outbox_model=AuditOutbox)
            assert len(batch) == 3
            ids = [row.id for row in batch]
            await reader.mark_processed(
                session, ids, outbox_model=AuditOutbox
            )

    # Refetch — empty
    async with session_factory() as session:
        async with session.begin():
            batch = await reader.fetch_batch(session, outbox_model=AuditOutbox)
            assert len(batch) == 0

    # Verify processed=true in DB
    async with session_factory() as session:
        result = await session.execute(
            sa.select(sa.func.count())
            .select_from(AuditOutbox)
            .where(AuditOutbox.processed == sa.true())
        )
        assert result.scalar() == 3


# --- Cleanup / Retention tests (US-005) ---


async def test_cleanup_deletes_old_processed_records(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Old processed records are deleted, recent ones are kept."""
    reader = OutboxReader(session_factory, batch_size=10)

    now = datetime.datetime.now(datetime.UTC)
    old_ts = now - datetime.timedelta(hours=100)
    recent_ts = now - datetime.timedelta(hours=10)

    async with session_factory() as session:
        async with session.begin():
            # Old processed — should be deleted
            await _insert_outbox_record(
                session, processed=True, timestamp=old_ts
            )
            # Recent processed — should be kept
            await _insert_outbox_record(
                session, processed=True, timestamp=recent_ts
            )
            # Old unprocessed — should be kept (not processed)
            await _insert_outbox_record(
                session, processed=False, timestamp=old_ts
            )

    # Run cleanup with 72-hour retention
    async with session_factory() as session:
        async with session.begin():
            deleted = await reader.cleanup_old_records(
                session, outbox_model=AuditOutbox, retention_hours=72
            )

    assert deleted == 1

    # Verify remaining records
    async with session_factory() as session:
        result = await session.execute(
            sa.select(sa.func.count()).select_from(AuditOutbox)
        )
        assert result.scalar() == 2


async def test_cleanup_with_no_old_records(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Cleanup returns 0 when there are no old processed records."""
    reader = OutboxReader(session_factory, batch_size=10)

    now = datetime.datetime.now(datetime.UTC)

    async with session_factory() as session:
        async with session.begin():
            await _insert_outbox_record(
                session, processed=True, timestamp=now
            )
            await _insert_outbox_record(
                session, processed=False, timestamp=now
            )

    async with session_factory() as session:
        async with session.begin():
            deleted = await reader.cleanup_old_records(
                session, outbox_model=AuditOutbox, retention_hours=72
            )

    assert deleted == 0


async def test_cleanup_on_empty_table(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Cleanup on empty table returns 0."""
    reader = OutboxReader(session_factory, batch_size=10)

    async with session_factory() as session:
        async with session.begin():
            deleted = await reader.cleanup_old_records(
                session, outbox_model=AuditOutbox, retention_hours=72
            )

    assert deleted == 0
