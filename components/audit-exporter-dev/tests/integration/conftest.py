"""Shared fixtures and helpers for integration tests.

Provides:
- Session-scoped testcontainers (PostgreSQL × 2, ClickHouse × 1)
- Environment variable builders for ``AppSettings`` construction
- Bootstrap environment fixtures (real containers / mocked)
- ClickHouse destination table helpers
- PostgreSQL audit_outbox seeding helpers
- ``BootstrapRuntimeState`` builder
- ``DummyClickHouseBackend`` for probe/unit-style tests
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import TYPE_CHECKING

import asyncpg
import clickhouse_connect
import pytest
from testcontainers.clickhouse import ClickHouseContainer
from testcontainers.postgres import PostgresContainer

from src.clickhouse.client import DESTINATION_TABLE, ClickHouseClient
from src.core.config import AppSettings, SourceName
from src.core.state import BootstrapRuntimeState
from src.db.source_connections import (
    DependencyProbeResult,
    PostgresBootstrapResult,
    build_postgres_reader,
)

if TYPE_CHECKING:
    pass

# Container images

CH_IMAGE = "clickhouse/clickhouse-server:24-alpine"
PG_IMAGE = "postgres:16-alpine"


# Session-scoped testcontainers


@pytest.fixture(scope="session")
def postgres_container_sap() -> Iterator[PostgresContainer]:
    """PostgreSQL container used as the SAP source database."""
    with PostgresContainer(PG_IMAGE) as container:
        yield container


@pytest.fixture(scope="session")
def postgres_container_zup() -> Iterator[PostgresContainer]:
    """PostgreSQL container used as the ZUP (and optionally UMTS) source database."""
    with PostgresContainer(PG_IMAGE) as container:
        yield container


@pytest.fixture(scope="session")
def clickhouse_container() -> Iterator[ClickHouseContainer]:
    """ClickHouse container used as the export destination."""
    with ClickHouseContainer(CH_IMAGE).with_exposed_ports(8123) as container:
        yield container


# Derived fixtures


@pytest.fixture
def ch_client(clickhouse_container: ClickHouseContainer) -> clickhouse_connect.driver.Client:
    """Raw clickhouse-connect client pointed at the test container."""
    return clickhouse_connect.get_client(
        host=clickhouse_container.get_container_host_ip(),
        port=int(clickhouse_container.get_exposed_port(8123)),
        database="default",
        username=clickhouse_container.username or "default",
        password=clickhouse_container.password or "",
        secure=False,
    )


# Environment variable builders


def pg_env_vars(source_name: str, container: PostgresContainer) -> dict[str, str]:
    """Build env vars for a real PostgresSourceSettings container.

    Produces keys like ``SAP__POSTGRES_HOST`` matching the pydantic-settings prefix.
    """
    prefix = source_name.upper()
    return {
        f"{prefix}__POSTGRES_HOST": str(container.get_container_host_ip()),
        f"{prefix}__POSTGRES_PORT": str(container.get_exposed_port(5432)),
        f"{prefix}__POSTGRES_DATABASE": str(container.dbname),
        f"{prefix}__POSTGRES_USER": str(container.username),
        f"{prefix}__POSTGRES_PASSWORD": str(container.password),
    }


def fake_pg_env_vars(
    source_name: str,
    *,
    host: str = "fake-db",
    port: str = "5432",
    database: str = "audit_db",
    user: str = "reader",
    password: str = "secret",
) -> dict[str, str]:
    """Build env vars with fake values (for mock-based tests or unreachable sources)."""
    prefix = source_name.upper()
    return {
        f"{prefix}__POSTGRES_HOST": host,
        f"{prefix}__POSTGRES_PORT": port,
        f"{prefix}__POSTGRES_DATABASE": database,
        f"{prefix}__POSTGRES_USER": user,
        f"{prefix}__POSTGRES_PASSWORD": password,
    }


def ch_env_vars(container: ClickHouseContainer) -> dict[str, str]:
    """Build ClickHouse env vars from a real container."""
    return {
        "CLICKHOUSE_HOST": str(container.get_container_host_ip()),
        "CLICKHOUSE_PORT": str(container.get_exposed_port(8123)),
        "CLICKHOUSE_DATABASE": "default",
        "CLICKHOUSE_USER": container.username or "default",
        "CLICKHOUSE_PASSWORD": container.password or "",
        "CLICKHOUSE_SECURE": "false",
    }


FAKE_CH_ENV: dict[str, str] = {
    "CLICKHOUSE_HOST": "clickhouse",
    "CLICKHOUSE_PORT": "8123",
    "CLICKHOUSE_DATABASE": "audit_exports",
    "CLICKHOUSE_USER": "default",
    "CLICKHOUSE_PASSWORD": "ch-secret",
    "CLICKHOUSE_SECURE": "false",
}


def _apply_env(monkeypatch: pytest.MonkeyPatch, values: dict[str, str]) -> None:
    for key, value in values.items():
        monkeypatch.setenv(key, value)


# Bootstrap environment fixtures


@pytest.fixture
def bootstrap_env_sap_ch(
    monkeypatch: pytest.MonkeyPatch,
    postgres_container_sap: PostgresContainer,
    clickhouse_container: ClickHouseContainer,
) -> None:
    """SAP → real container, ZUP/UMTS → fake, CH → real container."""
    _apply_env(
        monkeypatch,
        {
            **pg_env_vars("SAP", postgres_container_sap),
            **fake_pg_env_vars(
                "ZUP",
                host="zup-db",
                database="audit_zup",
                user="zup_reader",
                password="zup-secret",
            ),
            **fake_pg_env_vars(
                "UMTS",
                host="umts-db",
                database="audit_umts",
                user="umts_reader",
                password="umts-secret",
            ),
            **ch_env_vars(clickhouse_container),
            "DEPENDENCY_CONNECT_TIMEOUT_SECONDS": "5.0",
            "SOURCE_POLL_BATCH_SIZE": "10",
        },
    )


@pytest.fixture
def bootstrap_env_all_healthy(
    monkeypatch: pytest.MonkeyPatch,
    postgres_container_sap: PostgresContainer,
    postgres_container_zup: PostgresContainer,
    clickhouse_container: ClickHouseContainer,
) -> None:
    """All 3 PG sources healthy (UMTS reuses ZUP container), CH healthy."""
    _apply_env(
        monkeypatch,
        {
            **pg_env_vars("SAP", postgres_container_sap),
            **pg_env_vars("ZUP", postgres_container_zup),
            **pg_env_vars("UMTS", postgres_container_zup),
            **ch_env_vars(clickhouse_container),
            "SOURCE_POLL_INTERVAL_SECONDS": "0.1",
            "DEPENDENCY_CONNECT_TIMEOUT_SECONDS": "2.0",
            "SOURCE_POLL_BATCH_SIZE": "10",
        },
    )


@pytest.fixture
def bootstrap_env_with_bad_umts(
    monkeypatch: pytest.MonkeyPatch,
    postgres_container_sap: PostgresContainer,
    postgres_container_zup: PostgresContainer,
    clickhouse_container: ClickHouseContainer,
) -> None:
    """SAP + ZUP healthy, UMTS permanently unreachable, CH healthy."""
    _apply_env(
        monkeypatch,
        {
            **pg_env_vars("SAP", postgres_container_sap),
            **pg_env_vars("ZUP", postgres_container_zup),
            **fake_pg_env_vars(
                "UMTS",
                host="umts-nonexistent-host",
                database="audit_umts",
                user="umts_reader",
                password="umts-secret",
            ),
            **ch_env_vars(clickhouse_container),
            "SOURCE_POLL_INTERVAL_SECONDS": "0.1",
            "DEPENDENCY_CONNECT_TIMEOUT_SECONDS": "2.0",
            "SOURCE_POLL_BATCH_SIZE": "10",
        },
    )


@pytest.fixture
def bootstrap_env_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """All env vars fake — for tests using mocked dependencies (no containers needed)."""
    _apply_env(
        monkeypatch,
        {
            **fake_pg_env_vars(
                "SAP",
                host="sap-db",
                database="audit_sap",
                user="sap_reader",
                password="sap-secret",
            ),
            **fake_pg_env_vars(
                "ZUP",
                host="zup-db",
                database="audit_zup",
                user="zup_reader",
                password="zup-secret",
            ),
            **fake_pg_env_vars(
                "UMTS",
                host="umts-db",
                database="audit_umts",
                user="umts_reader",
                password="umts-secret",
            ),
            **FAKE_CH_ENV,
            "DEPENDENCY_CONNECT_TIMEOUT_SECONDS": "1.5",
        },
    )


# DummyClickHouseBackend (for tests that mock CH instead of using a container)


class DummyClickHouseBackend:
    """Minimal stand-in for ``clickhouse_connect.driver.Client``."""

    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.closed = False

    def command(self, cmd: str) -> int:
        if self._error is not None:
            raise self._error
        assert cmd == "SELECT 1"
        return 1

    def close(self) -> None:
        self.closed = True


# ClickHouse destination table helpers


def create_destination_table(client: clickhouse_connect.driver.Client) -> None:
    """Create / recreate the ClickHouse destination table with dedup window."""
    client.command(f"DROP TABLE IF EXISTS {DESTINATION_TABLE}")
    client.command(f"""
        CREATE TABLE {DESTINATION_TABLE} (
            source_name  String,
            outbox_id    String,
            entity_type  String,
            entity_id    String,
            operation    String,
            old_values   Nullable(String),
            new_values   Nullable(String),
            user_id      Nullable(String),
            timestamp    DateTime,
            service_name String
        ) ENGINE = MergeTree()
        ORDER BY (source_name, outbox_id)
        SETTINGS non_replicated_deduplication_window = 1000
    """)


def total_destination_rows(client: clickhouse_connect.driver.Client) -> int:
    """Count total rows in the ClickHouse destination table."""
    return int(client.command(f"SELECT count() FROM {DESTINATION_TABLE}"))  # noqa: S608


def ch_source_names(client: clickhouse_connect.driver.Client) -> set[str]:
    """Return distinct ``source_name`` values from the destination table."""
    result = client.query(
        f"SELECT DISTINCT source_name FROM {DESTINATION_TABLE}",  # noqa: S608
    )
    return {row[0] for row in result.result_rows}


# PostgreSQL audit_outbox helpers

AUDIT_OUTBOX_DDL = """
CREATE TABLE audit_outbox (
    id UUID PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    old_values JSONB NULL,
    new_values JSONB NULL,
    user_id TEXT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    processed BOOLEAN NOT NULL,
    service_name TEXT NOT NULL
)
"""


async def connect_to_source(settings: AppSettings, source: SourceName) -> asyncpg.Connection:
    """Open a direct asyncpg connection to a source database."""
    s = settings.postgres_sources()[source]
    return await asyncpg.connect(
        host=s.host,
        port=s.port,
        user=s.user,
        password=s.password,
        database=s.database,
        timeout=s.connect_timeout_seconds,
    )


async def connect_to_container(container: PostgresContainer) -> asyncpg.Connection:
    """Open a direct asyncpg connection to a testcontainer."""
    return await asyncpg.connect(
        host=container.get_container_host_ip(),
        port=int(container.get_exposed_port(5432)),
        user=container.username,
        password=container.password,
        database=container.dbname,
        timeout=5.0,
    )


async def seed_audit_outbox(
    conn: asyncpg.Connection,
    rows: list[tuple],
) -> None:
    """Drop + create ``audit_outbox`` and insert seed rows.

    Each row tuple must contain 10 elements:
    ``(id, entity_type, entity_id, operation, old_values, new_values,
      user_id, timestamp, processed, service_name)``
    """
    await conn.execute("DROP TABLE IF EXISTS audit_outbox")
    await conn.execute(AUDIT_OUTBOX_DDL)
    for row in rows:
        await conn.execute(
            """
            INSERT INTO audit_outbox (
                id, entity_type, entity_id, operation,
                old_values, new_values, user_id,
                timestamp, processed, service_name
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            *row,
        )


async def query_processed_flags(
    conn: asyncpg.Connection,
) -> dict[str, bool]:
    """Return ``{str(id): processed}`` for all rows in ``audit_outbox``."""
    rows = await conn.fetch(
        "SELECT id, processed FROM audit_outbox ORDER BY timestamp ASC, id ASC",
    )
    return {row["id"]: row["processed"] for row in rows}


# BootstrapRuntimeState builder


def build_runtime_state(
    settings: AppSettings,
    ch_writer: ClickHouseClient | None = None,
    *,
    sources: dict[SourceName, bool] | None = None,
) -> BootstrapRuntimeState:
    """Build ``BootstrapRuntimeState`` with real readers.

    ``sources`` maps source name → probe-ok status.  Defaults to ``{sap: True}``.
    """
    if sources is None:
        sources = {SourceName.sap: True}

    all_source_settings = settings.postgres_sources()
    pg_readers = {name: build_postgres_reader(all_source_settings[name]) for name in sources}

    probe_results: dict[SourceName, DependencyProbeResult] = {}
    for name, ok in sources.items():
        s = all_source_settings[name]
        probe_results[name] = DependencyProbeResult(
            dependency=f"postgres:{name.value}",
            display_dsn=s.probe_dsn().full,
            ok=ok,
            message=(
                "probe succeeded"
                if ok
                else f"postgres source '{name.value}' probe failed: host unreachable"
            ),
        )

    ch_dsn = (
        settings.clickhouse().probe_dsn().full
        if ch_writer
        else "clickhouse://default:***@ch:8123/default"
    )
    return BootstrapRuntimeState.from_probe_results(
        settings=settings,
        postgres_readers=pg_readers,
        clickhouse_client=ch_writer,  # type: ignore[arg-type]
        postgres_probe=PostgresBootstrapResult(sources=probe_results),
        clickhouse_probe=DependencyProbeResult(
            dependency="clickhouse",
            display_dsn=ch_dsn,
            ok=True,
            message="probe succeeded",
        ),
    )


# Async ↔ sync bridge for TestClient-based tests


def run_async(coro):  # noqa: ANN001, ANN201
    """Run an async coroutine from a synchronous test context."""
    return asyncio.run(coro)
