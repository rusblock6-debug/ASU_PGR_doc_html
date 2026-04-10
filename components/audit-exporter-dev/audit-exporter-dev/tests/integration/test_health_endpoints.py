"""Integration tests for liveness and readiness HTTP endpoints."""

from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.clickhouse.client import ClickHouseClient
from src.core.config import SourceName
from src.core.state import AppLifecyclePhase
from src.db.source_connections import PostgresSourceReader
from tests.integration.conftest import DummyClickHouseBackend

# Mock factories


def _make_postgres_factory():  # noqa: ANN202
    def _factory(settings: object) -> PostgresSourceReader:
        return PostgresSourceReader(settings=settings)

    return _factory


def _make_pool_mock(*, failing_source: SourceName | None = None):  # noqa: ANN202
    """Build a mock for ``asyncpg.create_pool`` that optionally fails for one source."""

    async def _mock_create_pool(**kwargs):  # noqa: ANN003
        if failing_source is not None:
            host = kwargs.get("host", "")
            if failing_source.value in host:
                raise ConnectionRefusedError(
                    f"probe rejected password {kwargs.get('password', '')}",
                )

        pool = MagicMock()
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="SELECT 1")
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        pool.close = AsyncMock()
        return pool

    return _mock_create_pool


def _make_clickhouse_factory(*, failing: bool = False):  # noqa: ANN202
    def _factory(settings: object) -> ClickHouseClient:
        backend_error = None
        if failing:
            backend_error = RuntimeError(
                f"authentication failed for {settings.password}",
            )
        return ClickHouseClient(
            settings=settings,
            client=DummyClickHouseBackend(error=backend_error),
        )

    return _factory


# Tests


@pytest.mark.integration
def test_healthz_and_readyz_report_healthy_runtime(bootstrap_env_mocked: None) -> None:
    with ExitStack() as stack:
        stack.enter_context(
            patch("src.app.build_postgres_reader", side_effect=_make_postgres_factory()),
        )
        stack.enter_context(
            patch("src.app.build_clickhouse_client", side_effect=_make_clickhouse_factory()),
        )
        stack.enter_context(
            patch(
                "src.db.source_connections.asyncpg.create_pool",
                side_effect=_make_pool_mock(),
            ),
        )

        from src.main import app

        with TestClient(app) as client:
            health_response = client.get("/healthz")
            ready_response = client.get("/readyz")

            assert health_response.status_code == 200
            assert health_response.json() == {
                "status": "ok",
                "live": True,
                "phase": AppLifecyclePhase.ready.value,
                "startup_complete": True,
            }

            assert ready_response.status_code == 200
            body = ready_response.json()
            assert body["ready"] is True
            assert body["phase"] == AppLifecyclePhase.ready.value
            assert body["startup_complete"] is True
            assert set(body["dependencies"]["postgres"]) == {"sap", "zup", "umts"}
            assert body["dependencies"]["postgres"]["sap"]["dependency"] == "postgres:sap"
            assert body["dependencies"]["clickhouse"]["dependency"] == "clickhouse"
            assert "***" in body["dependencies"]["clickhouse"]["display_dsn"]
            assert "ch-secret" not in str(body)

        runtime_state = app.state.runtime_state
        assert runtime_state.phase == AppLifecyclePhase.stopped
        assert runtime_state.clickhouse_client is not None
        assert runtime_state.clickhouse_client.client.closed is True


@pytest.mark.integration
def test_readyz_reports_dependency_failure_but_healthz_stays_live(
    bootstrap_env_mocked: None,
) -> None:
    with ExitStack() as stack:
        stack.enter_context(
            patch("src.app.build_postgres_reader", side_effect=_make_postgres_factory()),
        )
        stack.enter_context(
            patch("src.app.build_clickhouse_client", side_effect=_make_clickhouse_factory()),
        )
        stack.enter_context(
            patch(
                "src.db.source_connections.asyncpg.create_pool",
                side_effect=_make_pool_mock(failing_source=SourceName.zup),
            ),
        )

        from src.main import app

        with TestClient(app) as client:
            health_response = client.get("/healthz")
            ready_response = client.get("/readyz")

            assert health_response.status_code == 200
            assert health_response.json()["live"] is True
            assert health_response.json()["phase"] == AppLifecyclePhase.degraded.value

            assert ready_response.status_code == 503
            body = ready_response.json()
            assert body["ready"] is False
            assert body["phase"] == AppLifecyclePhase.degraded.value
            assert body["dependencies"]["postgres"]["zup"]["ok"] is False
            assert body["dependencies"]["postgres"]["zup"]["dependency"] == "postgres:zup"
            assert "probe failed" in body["dependencies"]["postgres"]["zup"]["message"]
            assert "zup-secret" not in body["dependencies"]["postgres"]["zup"]["message"]
            assert "***" in body["dependencies"]["postgres"]["zup"]["message"]
            assert body["dependencies"]["clickhouse"]["ok"] is True
