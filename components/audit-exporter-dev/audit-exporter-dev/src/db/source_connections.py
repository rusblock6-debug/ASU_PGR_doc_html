"""Typed connectivity primitives and ordered polling contracts for PostgreSQL sources."""

import asyncio
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import asyncpg
from pydantic import BaseModel, ConfigDict

from src.core.config import PostgresSourceSettings, SourceName
from src.core.diagnostics import redacted_failure_message

_READ_UNPROCESSED_AUDIT_OUTBOX_SQL = """
SELECT
    id,
    entity_type,
    entity_id,
    operation,
    old_values,
    new_values,
    user_id,
    timestamp,
    processed,
    service_name
FROM audit_outbox
WHERE processed = false
ORDER BY timestamp ASC, id ASC
LIMIT $1
"""


class DependencyProbeResult(BaseModel):
    """Structured dependency probe outcome safe for readiness reporting."""

    dependency: str
    display_dsn: str
    ok: bool
    message: str


class SourceAuditOutboxRow(BaseModel):
    """Typed source-side row read from a PostgreSQL audit_outbox table."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    entity_type: str
    entity_id: str
    operation: str
    old_values: dict[str, object] | None
    new_values: dict[str, object] | None
    user_id: str | None
    timestamp: datetime
    processed: bool
    service_name: str


class ExportedAuditEvent(BaseModel):
    """Canonical exported event shape derived from one source audit_outbox row."""

    model_config = ConfigDict(frozen=True)

    source_name: SourceName
    outbox_id: UUID
    entity_type: str
    entity_id: str
    operation: str
    old_values: dict[str, object] | None
    new_values: dict[str, object] | None
    user_id: str | None
    timestamp: datetime
    service_name: str


class AcknowledgementOutcome(BaseModel):
    """Structured outcome from a source row acknowledgement attempt."""

    model_config = ConfigDict(frozen=True)

    source_name: SourceName
    acknowledged_count: int
    ok: bool
    error_message: str | None
    acknowledged_at: datetime


class SourcePollResult(BaseModel):
    """Inspectable result for one ordered source poll attempt."""

    source_name: SourceName
    batch_size: int
    row_count: int
    polled_at: datetime
    highest_seen_timestamp: datetime | None
    highest_seen_outbox_id: UUID | None


def _pg_failure_message(settings: PostgresSourceSettings, exc: Exception) -> str:
    """Render a password-safe PostgreSQL failure message."""
    return redacted_failure_message(
        dependency=f"postgres source '{settings.name.value}'",
        dsn_without_credentials=settings.probe_dsn().without_credentials,
        password=settings.password,
        exc=exc,
    )


@dataclass
class PostgresSourceReader:
    """Read ordered, unacknowledged audit_outbox rows for one configured source."""

    settings: PostgresSourceSettings
    _pool: asyncpg.Pool | None = None

    @property
    def source_name(self) -> SourceName:
        """Return the fixed configured source identity."""
        return self.settings.name

    async def _get_pool(self) -> asyncpg.Pool:
        """Return the connection pool, creating it lazily on first use."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=self.settings.host,
                port=self.settings.port,
                user=self.settings.user,
                password=self.settings.password,
                database=self.settings.database,
                min_size=1,
                max_size=3,
                command_timeout=self.settings.connect_timeout_seconds,
            )
        return self._pool

    async def fetch_unprocessed_rows(self, *, batch_size: int) -> list[SourceAuditOutboxRow]:
        """Return the next ordered batch of unprocessed source rows."""
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            records = await connection.fetch(_READ_UNPROCESSED_AUDIT_OUTBOX_SQL, batch_size)

        return [
            SourceAuditOutboxRow.model_validate(_normalize_record_payload(dict(record)))
            for record in records
        ]

    async def fetch_export_batch(self, *, batch_size: int) -> list[ExportedAuditEvent]:
        """Return canonical exported events for the next ordered source batch."""
        rows = await self.fetch_unprocessed_rows(batch_size=batch_size)
        return [
            ExportedAuditEvent(
                source_name=self.source_name,
                outbox_id=row.id,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                operation=row.operation,
                old_values=row.old_values,
                new_values=row.new_values,
                user_id=row.user_id,
                timestamp=row.timestamp,
                service_name=row.service_name,
            )
            for row in rows
        ]

    async def poll(self, *, batch_size: int) -> tuple[list[ExportedAuditEvent], SourcePollResult]:
        """Read one ordered export batch together with a diagnostic poll snapshot."""
        exported_events = await self.fetch_export_batch(batch_size=batch_size)
        highest_event = exported_events[-1] if exported_events else None
        return exported_events, SourcePollResult(
            source_name=self.source_name,
            batch_size=batch_size,
            row_count=len(exported_events),
            polled_at=datetime.now(tz=UTC),
            highest_seen_timestamp=highest_event.timestamp if highest_event is not None else None,
            highest_seen_outbox_id=highest_event.outbox_id if highest_event is not None else None,
        )

    async def acknowledge_rows(self, outbox_ids: list[UUID]) -> AcknowledgementOutcome:
        """Mark source audit_outbox rows as processed after confirmed downstream write."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as connection:
                result: str = await connection.execute(
                    "UPDATE audit_outbox SET processed = true WHERE id = ANY($1::uuid[])",
                    outbox_ids,
                )
            count = int(result.split()[-1])
            return AcknowledgementOutcome(
                source_name=self.source_name,
                acknowledged_count=count,
                ok=True,
                error_message=None,
                acknowledged_at=datetime.now(tz=UTC),
            )
        except Exception as exc:  # noqa: BLE001
            return AcknowledgementOutcome(
                source_name=self.source_name,
                acknowledged_count=0,
                ok=False,
                error_message=_pg_failure_message(self.settings, exc),
                acknowledged_at=datetime.now(tz=UTC),
            )

    async def probe(self) -> DependencyProbeResult:
        """Verify the source is reachable with a minimal round-trip query."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as connection:
                await connection.execute("SELECT 1")
        except Exception as exc:  # noqa: BLE001
            return DependencyProbeResult(
                dependency=f"postgres:{self.settings.name.value}",
                display_dsn=self.settings.probe_dsn().full,
                ok=False,
                message=_pg_failure_message(self.settings, exc),
            )

        return DependencyProbeResult(
            dependency=f"postgres:{self.settings.name.value}",
            display_dsn=self.settings.probe_dsn().full,
            ok=True,
            message="probe succeeded",
        )

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None


class PostgresBootstrapResult(BaseModel):
    """Aggregated bootstrap status across all PostgreSQL sources."""

    sources: dict[SourceName, DependencyProbeResult]

    @property
    def ok(self) -> bool:
        """Return true when all sources probed successfully."""
        return all(result.ok for result in self.sources.values())


def build_postgres_reader(settings: PostgresSourceSettings) -> PostgresSourceReader:
    """Create a typed PostgreSQL source reader for one configured source."""
    return PostgresSourceReader(settings=settings)


async def probe_postgres_sources(
    readers: Mapping[SourceName, PostgresSourceReader],
) -> PostgresBootstrapResult:
    """Probe every configured PostgreSQL source concurrently."""
    probe_tasks = {source_name: reader.probe() for source_name, reader in readers.items()}
    results = dict(
        zip(probe_tasks.keys(), await asyncio.gather(*probe_tasks.values()), strict=True),
    )
    return PostgresBootstrapResult(sources=results)


async def close_postgres_sources(readers: Mapping[SourceName, PostgresSourceReader]) -> None:
    """Close all PostgreSQL source connection pools."""
    for reader in readers.values():
        await reader.close()


def _normalize_record_payload(payload: dict[str, object]) -> dict[str, object]:
    """Normalize driver-returned payload values into the canonical row contract."""
    for key in ("old_values", "new_values"):
        value = payload.get(key)
        if isinstance(value, str):
            payload[key] = json.loads(value)
    return payload
