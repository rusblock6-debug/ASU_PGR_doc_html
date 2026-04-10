"""Outbox daemon: polls audit_outbox and publishes to RabbitMQ Stream."""

from __future__ import annotations

import asyncio
import logging
import signal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from audit_lib.daemon.publisher import StreamPublisher
from audit_lib.daemon.reader import OutboxReader
from audit_lib.daemon.serialization import serialize_outbox_record

logger = logging.getLogger(__name__)


class OutboxDaemon:
    """Daemon that polls audit_outbox and publishes to RabbitMQ Stream.

    Usage::

        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from audit_lib.daemon import OutboxDaemon
        from audit_lib.models import create_audit_model

        engine = create_async_engine("postgresql+asyncpg://...")
        session_factory = async_sessionmaker(engine)

        # AuditOutbox must be created via create_audit_model(Base)
        daemon = OutboxDaemon(
            session_factory=session_factory,
            outbox_model=AuditOutbox,
            host="localhost",
            port=5552,
            stream_name="audit-events",
        )
        await daemon.run()

    Parameters
    ----------
    session_factory:
        An async sessionmaker bound to an ``AsyncEngine``.
    outbox_model:
        The ``AuditOutbox`` SQLAlchemy model class (from ``create_audit_model``).
    host:
        RabbitMQ host.
    port:
        RabbitMQ Stream protocol port.
    username:
        RabbitMQ username.
    password:
        RabbitMQ password.
    vhost:
        RabbitMQ virtual host.
    stream_name:
        Name of the target RabbitMQ stream.
    batch_size:
        Maximum number of outbox records per batch.
    poll_interval:
        Seconds to sleep between polling cycles.
    max_backoff:
        Maximum backoff time in seconds for retry on publish failure.
    retention_hours:
        Hours to keep processed records before cleanup. ``None`` disables cleanup.
    cleanup_interval_hours:
        How often (in hours) to run the cleanup task.
    """

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        outbox_model: type[Any],
        host: str = "localhost",
        port: int = 5552,
        username: str = "guest",
        password: str = "guest",
        vhost: str = "/",
        stream_name: str = "audit-events",
        batch_size: int = 100,
        poll_interval: float = 1.0,
        max_backoff: float = 60.0,
        retention_hours: int | None = 72,
        cleanup_interval_hours: float = 1.0,
    ) -> None:
        self._session_factory = session_factory
        self._outbox_model = outbox_model
        self._batch_size = batch_size
        self._poll_interval = poll_interval
        self._max_backoff = max_backoff
        self._retention_hours = retention_hours
        self._cleanup_interval_hours = cleanup_interval_hours
        self._running = False

        self._publisher = StreamPublisher(
            host=host,
            port=port,
            username=username,
            password=password,
            vhost=vhost,
            stream_name=stream_name,
        )
        self._reader = OutboxReader(
            session_factory=session_factory,
            batch_size=batch_size,
        )

    async def run(self) -> None:
        """Start the daemon loop.

        Polls the outbox table, serializes records to JSON, publishes
        them to RabbitMQ Stream, and marks them as processed. Retries
        with exponential backoff on publish failure.

        If ``retention_hours`` is set, a separate cleanup task
        periodically deletes old processed records.
        """
        self._running = True
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self.stop)

        logger.info("OutboxDaemon starting")

        cleanup_task: asyncio.Task[None] | None = None
        if self._retention_hours is not None:
            cleanup_task = asyncio.create_task(self._cleanup_loop())

        try:
            async with self._publisher:
                while self._running:
                    await self._poll_cycle()
        finally:
            if cleanup_task is not None:
                cleanup_task.cancel()
                try:
                    await cleanup_task
                except asyncio.CancelledError:
                    pass

        logger.info("OutboxDaemon stopped")

    async def _poll_cycle(self) -> None:
        """Execute one polling cycle: fetch, publish, mark processed."""
        async with self._session_factory() as session:
            async with session.begin():
                records = await self._reader.fetch_batch(
                    session, outbox_model=self._outbox_model
                )

            if not records:
                await asyncio.sleep(self._poll_interval)
                return

            await self._publish_with_retry(records)

            async with session.begin():
                await self._reader.mark_processed(
                    session,
                    [r.id for r in records],
                    outbox_model=self._outbox_model,
                )

        await asyncio.sleep(self._poll_interval)

    async def _publish_with_retry(self, records: list[Any]) -> None:
        """Publish records with infinite retry and exponential backoff."""
        backoff = 1.0

        while self._running:
            try:
                for record in records:
                    message = serialize_outbox_record(record)
                    await self._publisher.publish(message)
                logger.info("Published %d outbox records", len(records))
                return
            except Exception:
                logger.warning(
                    "Publish failed, retrying in %.1fs", backoff, exc_info=True
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self._max_backoff)

    async def _cleanup_loop(self) -> None:
        """Periodically delete old processed outbox records."""
        interval_seconds = self._cleanup_interval_hours * 3600
        assert self._retention_hours is not None  # guarded by caller
        while self._running:
            await asyncio.sleep(interval_seconds)
            if not self._running:
                break
            try:
                async with self._session_factory() as session:
                    async with session.begin():
                        await self._reader.cleanup_old_records(
                            session,
                            outbox_model=self._outbox_model,
                            retention_hours=self._retention_hours,
                        )
            except Exception:
                logger.error("Cleanup failed", exc_info=True)

    def stop(self) -> None:
        """Signal the daemon to stop gracefully."""
        logger.info("OutboxDaemon stop requested")
        self._running = False
