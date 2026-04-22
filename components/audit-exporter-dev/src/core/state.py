"""Lifespan-owned bootstrap state primitives."""

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from loguru import logger
from pydantic import BaseModel

from src.clickhouse.client import ClickHouseClient, ClickHouseWriteOutcome
from src.core.config import AppSettings, SourceName
from src.db.source_connections import (
    AcknowledgementOutcome,
    DependencyProbeResult,
    PostgresBootstrapResult,
    PostgresSourceReader,
    SourcePollResult,
    close_postgres_sources,
    probe_postgres_sources,
)


class AppLifecyclePhase(StrEnum):
    """Runtime lifecycle phase exposed through readiness diagnostics."""

    not_started = "not_started"
    starting = "starting"
    ready = "ready"
    degraded = "degraded"
    shutting_down = "shutting_down"
    stopped = "stopped"


class BootstrapProbeSnapshot(BaseModel):
    """Readiness-friendly probe snapshot for all bootstrap dependencies."""

    postgres: dict[SourceName, DependencyProbeResult]
    clickhouse: DependencyProbeResult

    @property
    def ok(self) -> bool:
        """Return true when every dependency probe succeeded."""
        return self.clickhouse.ok and all(result.ok for result in self.postgres.values())


class SourcePollingSnapshot(BaseModel):
    """Operator-facing polling ownership and latest result metadata."""

    configured_batch_size: int
    readers: list[SourceName]
    last_success_by_source: dict[SourceName, SourcePollResult]
    last_failure_by_source: dict[SourceName, str]
    updated_at: datetime | None


class ClickHouseWriteSnapshot(BaseModel):
    """Operator-facing ClickHouse write status snapshot."""

    last_success: ClickHouseWriteOutcome | None = None
    last_failure: ClickHouseWriteOutcome | None = None
    total_writes: int = 0
    total_rows_written: int = 0
    updated_at: datetime | None = None


class AcknowledgementSnapshot(BaseModel):
    """Operator-facing acknowledgement tracking per source."""

    last_success_by_source: dict[SourceName, AcknowledgementOutcome] = {}
    last_failure_by_source: dict[SourceName, str] = {}
    total_acknowledged: int = 0
    updated_at: datetime | None = None


@dataclass
class BootstrapRuntimeState:
    """Runtime-owned bootstrap objects and their latest probe state."""

    settings: AppSettings | None
    postgres_readers: dict[SourceName, PostgresSourceReader]
    clickhouse_client: ClickHouseClient | None
    probes: BootstrapProbeSnapshot | None
    polling: SourcePollingSnapshot | None
    clickhouse_writes: ClickHouseWriteSnapshot | None
    acknowledgements: AcknowledgementSnapshot | None
    phase: AppLifecyclePhase
    startup_complete: bool

    @classmethod
    def not_started(cls) -> Self:
        """Create the empty pre-startup runtime state used before lifespan begins."""
        return cls(
            settings=None,
            postgres_readers={},
            clickhouse_client=None,
            probes=None,
            polling=None,
            clickhouse_writes=None,
            acknowledgements=None,
            phase=AppLifecyclePhase.not_started,
            startup_complete=False,
        )

    @classmethod
    def from_probe_results(
        cls,
        *,
        settings: AppSettings,
        postgres_readers: dict[SourceName, PostgresSourceReader],
        clickhouse_client: ClickHouseClient,
        postgres_probe: PostgresBootstrapResult,
        clickhouse_probe: DependencyProbeResult,
    ) -> Self:
        """Assemble runtime state from initialized readers and probe outcomes."""
        probes = BootstrapProbeSnapshot(
            postgres=postgres_probe.sources,
            clickhouse=clickhouse_probe,
        )
        polling = SourcePollingSnapshot(
            configured_batch_size=settings.source_poll_batch_size,
            readers=list(postgres_readers),
            last_success_by_source={},
            last_failure_by_source={},
            updated_at=None,
        )
        state = cls(
            settings=settings,
            postgres_readers=postgres_readers,
            clickhouse_client=clickhouse_client,
            probes=probes,
            polling=polling,
            clickhouse_writes=ClickHouseWriteSnapshot(),
            acknowledgements=AcknowledgementSnapshot(),
            phase=AppLifecyclePhase.starting,
            startup_complete=True,
        )
        state.set_phase(
            AppLifecyclePhase.ready if probes.ok else AppLifecyclePhase.degraded,
        )
        return state

    def set_phase(self, new_phase: AppLifecyclePhase) -> None:
        """Transition to *new_phase*, logging the change when it differs."""
        old_phase = self.phase
        if old_phase == new_phase:
            return
        self.phase = new_phase
        logger.info(
            "phase_changed",
            old_phase=old_phase.value,
            new_phase=new_phase.value,
        )

    @property
    def ready(self) -> bool:
        """Return true when startup finished and runtime phase is ready."""
        return self.startup_complete and self.phase == AppLifecyclePhase.ready

    def update_phase_from_runtime_health(self) -> None:
        """Set phase to degraded/ready based on per-source runtime failure state.

        Lifecycle-terminal phases (``not_started``, ``shutting_down``, ``stopped``)
        and incomplete startup are never overridden.
        """
        if not self.startup_complete:
            return
        if self.phase in (
            AppLifecyclePhase.shutting_down,
            AppLifecyclePhase.stopped,
        ):
            return

        has_polling_failures = bool(
            self.polling and self.polling.last_failure_by_source,
        )
        has_ack_failures = bool(
            self.acknowledgements and self.acknowledgements.last_failure_by_source,
        )

        if has_polling_failures or has_ack_failures:
            self.set_phase(AppLifecyclePhase.degraded)
        elif self.probes is not None and self.probes.ok:
            self.set_phase(AppLifecyclePhase.ready)

    def record_source_poll_success(self, result: SourcePollResult) -> None:
        """Record the latest successful poll metadata for one source."""
        if self.polling is None:
            return
        self.polling.last_success_by_source[result.source_name] = result
        self.polling.last_failure_by_source.pop(result.source_name, None)
        self.polling.updated_at = datetime.now(tz=UTC)

    def record_source_poll_failure(self, source_name: SourceName, message: str) -> None:
        """Record a password-safe poll failure message for one source."""
        if self.polling is None:
            return
        self.polling.last_failure_by_source[source_name] = message
        self.polling.updated_at = datetime.now(tz=UTC)

    def record_clickhouse_write(self, outcome: ClickHouseWriteOutcome) -> None:
        """Record the latest ClickHouse write outcome for observability."""
        if self.clickhouse_writes is None:
            return
        self.clickhouse_writes.total_writes += 1
        if outcome.ok:
            self.clickhouse_writes.last_success = outcome
            self.clickhouse_writes.total_rows_written += outcome.row_count
        else:
            self.clickhouse_writes.last_failure = outcome
        self.clickhouse_writes.updated_at = datetime.now(tz=UTC)

    def record_acknowledgement(self, outcome: AcknowledgementOutcome) -> None:
        """Record the latest acknowledgement outcome for one source."""
        if self.acknowledgements is None:
            return
        if outcome.ok:
            self.acknowledgements.last_success_by_source[outcome.source_name] = outcome
            self.acknowledgements.last_failure_by_source.pop(outcome.source_name, None)
            self.acknowledgements.total_acknowledged += outcome.acknowledged_count
        else:
            self.acknowledgements.last_failure_by_source[outcome.source_name] = (
                outcome.error_message or "unknown error"
            )
        self.acknowledgements.updated_at = datetime.now(tz=UTC)

    def readiness_payload(self) -> dict[str, object]:
        """Build a route-friendly readiness payload with per-dependency detail."""
        if self.probes is None:
            return {
                "ready": False,
                "phase": self.phase.value,
                "startup_complete": self.startup_complete,
                "dependencies": {
                    "postgres": {},
                    "clickhouse": None,
                },
                "polling": None,
                "clickhouse_writes": None,
                "acknowledgements": None,
            }

        return {
            "ready": self.ready,
            "phase": self.phase.value,
            "startup_complete": self.startup_complete,
            "dependencies": {
                "postgres": {
                    source_name.value: result.model_dump(mode="json")
                    for source_name, result in self.probes.postgres.items()
                },
                "clickhouse": self.probes.clickhouse.model_dump(mode="json"),
            },
            "polling": self.polling.model_dump(mode="json") if self.polling is not None else None,
            "clickhouse_writes": (
                self.clickhouse_writes.model_dump(mode="json")
                if self.clickhouse_writes is not None
                else None
            ),
            "acknowledgements": (
                self.acknowledgements.model_dump(mode="json")
                if self.acknowledgements is not None
                else None
            ),
        }


async def build_runtime_state(
    *,
    settings: AppSettings,
    postgres_readers: dict[SourceName, PostgresSourceReader],
    clickhouse_client: ClickHouseClient,
) -> BootstrapRuntimeState:
    """Probe all dependencies and produce the lifespan-owned runtime state."""
    pg_start = time.monotonic()
    postgres_probe = await probe_postgres_sources(postgres_readers)
    pg_duration_ms = round((time.monotonic() - pg_start) * 1000, 1)

    for source_name, result in postgres_probe.sources.items():
        logger.bind(source_name=source_name.value).info(
            "dependency_probe",
            dependency="postgres",
            status="ok" if result.ok else "failed",
            duration_ms=pg_duration_ms,
        )

    ch_start = time.monotonic()
    clickhouse_probe = await clickhouse_client.probe()
    ch_duration_ms = round((time.monotonic() - ch_start) * 1000, 1)

    logger.info(
        "dependency_probe",
        dependency="clickhouse",
        status="ok" if clickhouse_probe.ok else "failed",
        duration_ms=ch_duration_ms,
    )

    return BootstrapRuntimeState.from_probe_results(
        settings=settings,
        postgres_readers=postgres_readers,
        clickhouse_client=clickhouse_client,
        postgres_probe=postgres_probe,
        clickhouse_probe=clickhouse_probe,
    )


async def shutdown_runtime_state(state: BootstrapRuntimeState) -> None:
    """Dispose all managed dependency clients during application shutdown."""
    logger.info("shutdown_initiated")
    state.set_phase(AppLifecyclePhase.shutting_down)
    await close_postgres_sources(state.postgres_readers)
    if state.clickhouse_client is not None:
        await state.clickhouse_client.close()
    state.set_phase(AppLifecyclePhase.stopped)
    logger.info("shutdown_complete")
