"""Batch reader for the audit_outbox table with row-level locking."""

from __future__ import annotations

import datetime
import logging
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class OutboxReader:
    """Reads unprocessed outbox records in batches using FOR UPDATE SKIP LOCKED.

    Parameters
    ----------
    session_factory:
        An async sessionmaker bound to an ``AsyncEngine``.
    batch_size:
        Maximum number of rows to fetch per batch.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        batch_size: int,
    ) -> None:
        self._session_factory = session_factory
        self._batch_size = batch_size

    async def fetch_batch(
        self,
        session: AsyncSession,
        *,
        outbox_model: type[Any],
    ) -> list[Any]:
        """Fetch a batch of unprocessed outbox records.

        Executes::

            SELECT ... FROM audit_outbox
            WHERE processed = false
            ORDER BY timestamp ASC
            LIMIT :batch_size
            FOR UPDATE SKIP LOCKED

        Parameters
        ----------
        session:
            Active async session (must be inside a transaction).
        outbox_model:
            The ``AuditOutbox`` SQLAlchemy model class.

        Returns
        -------
        list
            A list of ``AuditOutbox`` instances.
        """
        stmt = (
            sa.select(outbox_model)
            .where(outbox_model.processed == sa.false())
            .order_by(outbox_model.timestamp.asc())
            .limit(self._batch_size)
            .with_for_update(skip_locked=True)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def mark_processed(
        self,
        session: AsyncSession,
        ids: list[UUID],
        *,
        outbox_model: type[Any],
    ) -> None:
        """Mark outbox records as processed.

        Executes::

            UPDATE audit_outbox SET processed = true WHERE id IN (:ids)

        Parameters
        ----------
        session:
            Active async session (must be inside a transaction).
        ids:
            List of record UUIDs to mark as processed.
        outbox_model:
            The ``AuditOutbox`` SQLAlchemy model class.
        """
        if not ids:
            return
        stmt = (
            sa.update(outbox_model)
            .where(outbox_model.id.in_(ids))
            .values(processed=True)
        )
        await session.execute(stmt)

    async def cleanup_old_records(
        self,
        session: AsyncSession,
        *,
        outbox_model: type[Any],
        retention_hours: int,
    ) -> int:
        """Delete old processed outbox records.

        Executes::

            DELETE FROM audit_outbox
            WHERE processed = true
              AND timestamp < now() - interval ':retention_hours hours'

        Parameters
        ----------
        session:
            Active async session (must be inside a transaction).
        outbox_model:
            The ``AuditOutbox`` SQLAlchemy model class.
        retention_hours:
            Records older than this many hours will be deleted.

        Returns
        -------
        int
            Number of deleted rows.
        """
        cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
            hours=retention_hours
        )
        stmt = (
            sa.delete(outbox_model)
            .where(outbox_model.processed == sa.true())
            .where(outbox_model.timestamp < cutoff)
        )
        result = await session.execute(stmt)
        count: int = result.rowcount  # type: ignore[attr-defined]
        logger.info("Cleaned up %d old outbox records", count)
        return count
