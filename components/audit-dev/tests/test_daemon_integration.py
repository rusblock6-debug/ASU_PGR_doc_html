"""Integration test: full outbox → RabbitMQ Stream cycle (US-007)."""

from __future__ import annotations

import asyncio
import datetime
import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from audit_lib.daemon.daemon import OutboxDaemon
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


async def _insert_record(
    session: AsyncSession,
    *,
    entity_type: str = "Order",
    entity_id: str | None = None,
    operation: str = "INSERT",
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    user_id: str = "test-user",
    service_name: str = "test-service",
    timestamp: datetime.datetime | None = None,
) -> Any:
    """Insert a test outbox record."""
    record = AuditOutbox(
        id=uuid.uuid4(),
        entity_type=entity_type,
        entity_id=entity_id or str(uuid.uuid4()),
        operation=operation,
        old_values=old_values,
        new_values=new_values or {"total": 100},
        user_id=user_id,
        timestamp=timestamp or datetime.datetime.now(datetime.UTC),
        processed=False,
        service_name=service_name,
    )
    session.add(record)
    await session.flush()
    return record


def _mock_producer_with_capture() -> tuple[MagicMock, list[bytes]]:
    """Create a mock rstream Producer class that captures messages."""
    published: list[bytes] = []
    mock_producer = AsyncMock()

    async def capture_send(
        *, stream: str, message: bytes
    ) -> None:
        published.append(message)

    mock_producer.send = AsyncMock(side_effect=capture_send)
    mock_cls = MagicMock(return_value=mock_producer)
    return mock_cls, published


async def _run_daemon_until(
    daemon: OutboxDaemon,
    condition: Any,
    timeout: float = 10.0,
) -> None:
    """Run the daemon until condition() is True or timeout."""

    async def wait_and_stop() -> None:
        for _ in range(500):
            await asyncio.sleep(0.02)
            if condition():
                daemon.stop()
                return
        daemon.stop()

    daemon_task = asyncio.create_task(daemon.run())
    stop_task = asyncio.create_task(wait_and_stop())
    await asyncio.wait_for(
        asyncio.gather(daemon_task, stop_task),
        timeout=timeout,
    )


@pytest.mark.integration
class TestDaemonFullCycle:
    """End-to-end: insert records → daemon → stream → processed."""

    @patch("audit_lib.daemon.publisher.Producer")
    async def test_records_published_and_marked_processed(
        self,
        mock_producer_cls: MagicMock,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Insert 3 records, daemon publishes all, marks processed."""
        mock_cls, published = _mock_producer_with_capture()
        mock_producer_cls.return_value = mock_cls.return_value

        async with session_factory() as session:
            async with session.begin():
                for i in range(3):
                    await _insert_record(
                        session,
                        entity_type=f"Entity{i}",
                        new_values={"index": i},
                    )

        daemon = OutboxDaemon(
            session_factory=session_factory,
            outbox_model=AuditOutbox,
            batch_size=10,
            poll_interval=0.01,
            retention_hours=None,
        )

        await _run_daemon_until(
            daemon, lambda: len(published) >= 3
        )

        # 3 messages published
        assert len(published) == 3

        # Each message is valid JSON with audit fields
        for msg_bytes in published:
            msg = json.loads(msg_bytes)
            assert "id" in msg
            assert "entity_type" in msg
            assert "operation" in msg
            assert "new_values" in msg
            assert "timestamp" in msg

        # All records marked processed in DB
        async with session_factory() as session:
            result = await session.execute(
                sa.select(sa.func.count())
                .select_from(AuditOutbox)
                .where(AuditOutbox.processed == sa.true())
            )
            assert result.scalar() == 3

        # No unprocessed records remain
        async with session_factory() as session:
            result = await session.execute(
                sa.select(sa.func.count())
                .select_from(AuditOutbox)
                .where(AuditOutbox.processed == sa.false())
            )
            assert result.scalar() == 0

    @patch("audit_lib.daemon.publisher.Producer")
    async def test_published_message_matches_record(
        self,
        mock_producer_cls: MagicMock,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Published JSON matches the original outbox record fields."""
        mock_cls, published = _mock_producer_with_capture()
        mock_producer_cls.return_value = mock_cls.return_value

        record_id = uuid.uuid4()
        ts = datetime.datetime(
            2026, 1, 15, 12, 0, 0, tzinfo=datetime.UTC
        )
        async with session_factory() as session:
            async with session.begin():
                record = AuditOutbox(
                    id=record_id,
                    entity_type="Invoice",
                    entity_id="inv-42",
                    operation="UPDATE",
                    old_values={"status": "draft"},
                    new_values={"status": "paid"},
                    user_id="admin",
                    timestamp=ts,
                    processed=False,
                    service_name="billing",
                )
                session.add(record)

        daemon = OutboxDaemon(
            session_factory=session_factory,
            outbox_model=AuditOutbox,
            batch_size=10,
            poll_interval=0.01,
            retention_hours=None,
        )

        await _run_daemon_until(
            daemon, lambda: len(published) >= 1
        )

        assert len(published) == 1
        msg = json.loads(published[0])
        assert msg["id"] == str(record_id)
        assert msg["entity_type"] == "Invoice"
        assert msg["entity_id"] == "inv-42"
        assert msg["operation"] == "UPDATE"
        assert msg["old_values"] == {"status": "draft"}
        assert msg["new_values"] == {"status": "paid"}
        assert msg["user_id"] == "admin"
        assert msg["service_name"] == "billing"
        assert msg["timestamp"] == "2026-01-15T12:00:00+00:00"

    @patch("audit_lib.daemon.publisher.Producer")
    async def test_graceful_shutdown_with_timeout(
        self,
        mock_producer_cls: MagicMock,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Daemon stops gracefully within timeout."""
        mock_producer_cls.return_value = AsyncMock()

        daemon = OutboxDaemon(
            session_factory=session_factory,
            outbox_model=AuditOutbox,
            batch_size=10,
            poll_interval=0.01,
            retention_hours=None,
        )

        async def delayed_stop() -> None:
            await asyncio.sleep(0.1)
            daemon.stop()

        daemon_task = asyncio.create_task(daemon.run())
        stop_task = asyncio.create_task(delayed_stop())

        await asyncio.wait_for(
            asyncio.gather(daemon_task, stop_task),
            timeout=5.0,
        )

        assert daemon._running is False

    @patch("audit_lib.daemon.publisher.Producer")
    async def test_daemon_processes_incrementally(
        self,
        mock_producer_cls: MagicMock,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Records inserted after daemon start are also processed."""
        mock_cls, published = _mock_producer_with_capture()
        mock_producer_cls.return_value = mock_cls.return_value

        # Insert initial record
        async with session_factory() as session:
            async with session.begin():
                await _insert_record(session, entity_type="First")

        daemon = OutboxDaemon(
            session_factory=session_factory,
            outbox_model=AuditOutbox,
            batch_size=10,
            poll_interval=0.01,
            retention_hours=None,
        )

        daemon_task = asyncio.create_task(daemon.run())

        # Wait for first record to be processed
        for _ in range(200):
            await asyncio.sleep(0.02)
            if len(published) >= 1:
                break

        # Insert second record while daemon is running
        async with session_factory() as session:
            async with session.begin():
                await _insert_record(session, entity_type="Second")

        # Wait for second record
        for _ in range(200):
            await asyncio.sleep(0.02)
            if len(published) >= 2:
                break

        daemon.stop()
        await asyncio.wait_for(daemon_task, timeout=5.0)

        assert len(published) == 2

        types = {
            json.loads(m)["entity_type"] for m in published
        }
        assert types == {"First", "Second"}
