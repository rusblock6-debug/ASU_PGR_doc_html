"""Typed connectivity and write primitives for the ClickHouse dependency."""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, cast

import anyio.to_thread
import clickhouse_connect
from pydantic import BaseModel

from src.core.config import ClickHouseSettings
from src.core.diagnostics import redacted_failure_message
from src.db.source_connections import DependencyProbeResult, ExportedAuditEvent

DESTINATION_TABLE = "audit_events"
DESTINATION_COLUMNS: list[str] = [
    "source_name",
    "outbox_id",
    "entity_type",
    "entity_id",
    "operation",
    "old_values",
    "new_values",
    "user_id",
    "timestamp",
    "service_name",
]


class ClickHouseProtocol(Protocol):
    """Subset of the client surface used by the bootstrap probe and writer."""

    def command(self, cmd: str) -> object:
        """Execute a ClickHouse command."""

    def insert(
        self,
        table: str | None = ...,
        data: Sequence[Sequence[Any]] = ...,  # type: ignore[assignment]
        column_names: str | Any = ...,  # type: ignore[assignment]
        **kwargs: Any,
    ) -> object:
        """Insert a batch of rows."""

    def close(self) -> None:
        """Close the client and free resources."""


class WriteResult(Protocol):
    """Minimal result surface returned by the driver's insert."""

    @property
    def written_rows(self) -> int: ...  # noqa: E704


class ClickHouseWriteOutcome(BaseModel):
    """Operator-facing write outcome for observability recording."""

    table: str
    row_count: int
    dedup_token: str
    written_at: datetime
    ok: bool
    error_message: str | None


def derive_dedup_token(events: Sequence[ExportedAuditEvent]) -> str:
    """Produce a stable, deterministic dedup token from ordered source identities.

    The token is a SHA-256 hex digest of the sorted ``(source_name, outbox_id)``
    pairs serialised as JSON.  Because the events are already ordered by the
    source reader, the sort here is a safety-net guarantee that the token is
    independent of any accidental reordering.
    """
    identity_pairs = sorted((event.source_name.value, str(event.outbox_id)) for event in events)
    payload = json.dumps(identity_pairs, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _event_to_row(event: ExportedAuditEvent) -> list[object]:
    """Serialise one exported event into the destination column order."""
    return [
        event.source_name.value,
        str(event.outbox_id),
        event.entity_type,
        event.entity_id,
        event.operation,
        json.dumps(event.old_values) if event.old_values is not None else None,
        json.dumps(event.new_values) if event.new_values is not None else None,
        event.user_id,
        event.timestamp,
        event.service_name,
    ]


@dataclass(frozen=True)
class ClickHouseClient:
    """Own the ClickHouse client, probe routine, and canonical batch writer."""

    settings: ClickHouseSettings
    client: ClickHouseProtocol

    async def probe(self) -> DependencyProbeResult:
        """Verify ClickHouse connectivity with a minimal command."""
        try:
            await anyio.to_thread.run_sync(self.client.command, "SELECT 1")
        except Exception as exc:  # noqa: BLE001
            return DependencyProbeResult(
                dependency="clickhouse",
                display_dsn=self.settings.probe_dsn().full,
                ok=False,
                message=_ch_failure_message(self.settings, exc),
            )

        return DependencyProbeResult(
            dependency="clickhouse",
            display_dsn=self.settings.probe_dsn().full,
            ok=True,
            message="probe succeeded",
        )

    async def insert_exported_events(
        self,
        events: Sequence[ExportedAuditEvent],
        *,
        table: str = DESTINATION_TABLE,
    ) -> ClickHouseWriteOutcome:
        """Insert canonical exported events with an explicit deduplication token.

        The token is derived from the ordered ``(source_name, outbox_id)``
        identities so that retrying the same logical batch is safely
        deduplicated by the ClickHouse engine.

        Returns a structured write outcome for observability recording.
        """
        if not events:
            return ClickHouseWriteOutcome(
                table=table,
                row_count=0,
                dedup_token="",
                written_at=datetime.now(tz=UTC),
                ok=True,
                error_message=None,
            )

        dedup_token = derive_dedup_token(events)
        rows = [_event_to_row(e) for e in events]

        def _sync_insert() -> object:
            return self.client.insert(
                table,
                rows,
                column_names=DESTINATION_COLUMNS,
                settings={"insert_deduplication_token": dedup_token},
            )

        try:
            await anyio.to_thread.run_sync(_sync_insert)
        except Exception as exc:  # noqa: BLE001
            return ClickHouseWriteOutcome(
                table=table,
                row_count=len(events),
                dedup_token=dedup_token,
                written_at=datetime.now(tz=UTC),
                ok=False,
                error_message=_ch_failure_message(self.settings, exc),
            )

        return ClickHouseWriteOutcome(
            table=table,
            row_count=len(events),
            dedup_token=dedup_token,
            written_at=datetime.now(tz=UTC),
            ok=True,
            error_message=None,
        )

    async def close(self) -> None:
        """Close the underlying ClickHouse client in a worker thread."""
        await anyio.to_thread.run_sync(self.client.close)


def build_clickhouse_client(settings: ClickHouseSettings) -> ClickHouseClient:
    """Create a typed ClickHouse client from validated settings."""
    raw_client = clickhouse_connect.get_client(**cast(dict[str, Any], settings.client_kwargs()))
    return ClickHouseClient(settings=settings, client=cast(ClickHouseProtocol, raw_client))


def _ch_failure_message(settings: ClickHouseSettings, exc: Exception) -> str:
    """Render a password-safe ClickHouse failure message."""
    return redacted_failure_message(
        dependency="clickhouse",
        dsn_without_credentials=settings.probe_dsn().without_credentials,
        password=settings.password,
        exc=exc,
    )
