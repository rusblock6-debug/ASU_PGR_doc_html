"""Integration tests for bootstrap configuration and dependency probes."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from src.clickhouse.client import ClickHouseClient
from src.core.config import AppSettings, SourceName, format_settings_validation_error
from src.core.state import BootstrapRuntimeState
from src.db.source_connections import build_postgres_reader, probe_postgres_sources
from tests.integration.conftest import DummyClickHouseBackend

# Helper: build a mock asyncpg pool that works with `async with pool.acquire()`


def _make_mock_pool() -> MagicMock:
    """Build a MagicMock pool where ``async with pool.acquire()`` yields a mock connection.

    ``pool.acquire()`` in asyncpg returns an async context manager (not a coroutine),
    so the pool must be a ``MagicMock`` — ``AsyncMock`` would wrap it in a coroutine.
    """
    pool = MagicMock()
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value="SELECT 1")
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    pool.close = AsyncMock()
    return pool


# Tests


@pytest.mark.integration
def test_settings_fail_fast_on_missing_clickhouse_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing required ClickHouse field causes a ValidationError at construction."""
    monkeypatch.setattr(
        AppSettings,
        "model_config",
        {**AppSettings.model_config, "env_file": None},
    )
    monkeypatch.delenv("CLICKHOUSE_HOST", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        AppSettings()

    message = format_settings_validation_error(exc_info.value)
    assert "clickhouse_host" in message


@pytest.mark.integration
def test_settings_fail_fast_on_invalid_postgres_source_host(
    bootstrap_env_mocked: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid (blank) Postgres source field causes a ValidationError via validate_contract."""
    monkeypatch.setenv("SAP__POSTGRES_HOST", "  ")

    with pytest.raises(ValidationError):
        AppSettings()


@pytest.mark.integration
def test_settings_normalize_fixed_sources_and_redact_dsns(bootstrap_env_mocked: None) -> None:
    settings = AppSettings()

    sources = settings.postgres_sources()
    assert tuple(sources) == tuple(SourceName)
    assert (
        sources[SourceName.sap]
        .async_sqlalchemy_dsn()
        .startswith("postgresql+asyncpg://sap_reader:")
    )
    assert (
        sources[SourceName.sap].probe_dsn().full
        == "postgresql://sap_reader:***@sap-db:5432/audit_sap"
    )
    assert "sap-secret" not in sources[SourceName.sap].probe_dsn().full

    clickhouse = settings.clickhouse()
    assert clickhouse.probe_dsn().full == "clickhouse://default:***@clickhouse:8123/audit_exports"
    assert "ch-secret" not in clickhouse.probe_dsn().full


@pytest.mark.integration
async def test_dependency_probes_surface_typed_redacted_results(
    bootstrap_env_mocked: None,
) -> None:
    settings = AppSettings()
    postgres_settings = settings.postgres_sources()
    postgres_readers = {name: build_postgres_reader(s) for name, s in postgres_settings.items()}
    clickhouse_client = ClickHouseClient(
        settings=settings.clickhouse(),
        client=DummyClickHouseBackend(),
    )

    mock_pool = _make_mock_pool()

    with patch(
        "src.db.source_connections.asyncpg.create_pool",
        AsyncMock(return_value=mock_pool),
    ):
        postgres_probe = await probe_postgres_sources(postgres_readers)
    clickhouse_probe = await clickhouse_client.probe()

    runtime_state = BootstrapRuntimeState.from_probe_results(
        settings=settings,
        postgres_readers=postgres_readers,
        clickhouse_client=clickhouse_client,
        postgres_probe=postgres_probe,
        clickhouse_probe=clickhouse_probe,
    )

    assert postgres_probe.ok is True
    assert clickhouse_probe.ok is True
    assert runtime_state.probes.ok is True
    assert runtime_state.probes.postgres[SourceName.zup].dependency == "postgres:zup"
    assert runtime_state.probes.clickhouse.dependency == "clickhouse"
    assert "***" in runtime_state.probes.clickhouse.display_dsn


@pytest.mark.integration
async def test_probe_failures_identify_dependency_without_leaking_passwords(
    bootstrap_env_mocked: None,
) -> None:
    settings = AppSettings()
    postgres_settings = settings.postgres_sources()
    postgres_readers = {name: build_postgres_reader(s) for name, s in postgres_settings.items()}
    clickhouse_password = settings.clickhouse().password
    clickhouse_client = ClickHouseClient(
        settings=settings.clickhouse(),
        client=DummyClickHouseBackend(
            error=RuntimeError(f"auth failed for password {clickhouse_password}"),
        ),
    )

    async def _mock_create_pool(**kwargs):  # noqa: ANN003
        name = None
        for sn, s in postgres_settings.items():
            if s.host == kwargs.get("host"):
                name = sn
                break

        if name is SourceName.zup:
            raise ConnectionRefusedError(
                f"could not connect using password {postgres_settings[SourceName.zup].password}",
            )

        return _make_mock_pool()

    with patch(
        "src.db.source_connections.asyncpg.create_pool",
        side_effect=_mock_create_pool,
    ):
        postgres_probe = await probe_postgres_sources(postgres_readers)
    clickhouse_probe = await clickhouse_client.probe()

    assert postgres_probe.ok is False
    assert postgres_probe.sources[SourceName.zup].dependency == "postgres:zup"
    assert "postgres source 'zup' probe failed" in postgres_probe.sources[SourceName.zup].message
    assert (
        postgres_settings[SourceName.zup].password
        not in postgres_probe.sources[SourceName.zup].message
    )
    assert "***" in postgres_probe.sources[SourceName.zup].message

    assert clickhouse_probe.ok is False
    assert clickhouse_probe.dependency == "clickhouse"
    assert "clickhouse probe failed" in clickhouse_probe.message
    assert clickhouse_password not in clickhouse_probe.message
    assert "***" in clickhouse_probe.message


@pytest.mark.integration
def test_postgres_reader_factory_builds_reader_with_correct_source(
    bootstrap_env_mocked: None,
) -> None:
    settings = AppSettings()
    reader = build_postgres_reader(settings.postgres_sources()[SourceName.sap])

    assert reader.settings.name is SourceName.sap
    assert reader._pool is None
    assert reader.settings.async_sqlalchemy_dsn().startswith(
        "postgresql+asyncpg://sap_reader:",
    )
