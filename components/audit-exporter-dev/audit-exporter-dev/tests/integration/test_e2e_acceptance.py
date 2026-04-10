"""End-to-end acceptance tests exercising the full FastAPI application lifecycle.

Unlike prior integration tests that call ``run_polling_loop()`` or
``process_source()`` directly, these tests boot the real app via
``TestClient(create_app(...))``, let the lifespan wire up real connections to
testcontainers, and verify outcomes through HTTP endpoints and direct DB queries.
"""

import time
from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer

from src.app import create_app
from tests.integration.conftest import (
    ch_source_names,
    connect_to_container,
    create_destination_table,
    run_async,
    seed_audit_outbox,
    total_destination_rows,
)

# Seed data

_SEED_ROW_IDS: dict[str, list[UUID]] = {
    "sap": [
        UUID("a0000000-0000-0000-0000-000000000001"),
        UUID("a0000000-0000-0000-0000-000000000002"),
    ],
    "zup": [
        UUID("b0000000-0000-0000-0000-000000000001"),
        UUID("b0000000-0000-0000-0000-000000000002"),
    ],
}


def _make_seed_rows(source_name: str, row_ids: list[UUID]) -> list[tuple]:
    return [
        (
            row_id,
            "invoice",
            f"inv-{source_name}-{i}",
            "insert",
            None,
            f'{{"status":"new","source":"{source_name}"}}',
            f"user-{source_name}-{i}",
            datetime(2026, 3, 17, 14, i, tzinfo=UTC),
            False,
            f"{source_name}-service",
        )
        for i, row_id in enumerate(row_ids, start=1)
    ]


# Helpers


async def _seed_container(container: PostgresContainer, source_name: str) -> None:
    """Seed audit_outbox on a container for a given source."""
    conn = await connect_to_container(container)
    try:
        await seed_audit_outbox(conn, _make_seed_rows(source_name, _SEED_ROW_IDS[source_name]))
    finally:
        await conn.close()


async def _query_processed_flags(
    container: PostgresContainer,
    row_ids: list[UUID],
) -> dict[UUID, bool]:
    """Return ``{row_id: processed}`` for the given outbox rows."""
    conn = await connect_to_container(container)
    try:
        rows = await conn.fetch(
            "SELECT id, processed FROM audit_outbox WHERE id = ANY($1::uuid[])",
            row_ids,
        )
        return {row["id"]: row["processed"] for row in rows}
    finally:
        await conn.close()


async def _reset_processed_flags(
    container: PostgresContainer,
    row_ids: list[UUID],
) -> None:
    """Reset ``processed=false`` for all given outbox rows."""
    conn = await connect_to_container(container)
    try:
        await conn.execute(
            "UPDATE audit_outbox SET processed = false WHERE id = ANY($1::uuid[])",
            row_ids,
        )
    finally:
        await conn.close()


# Tests


@pytest.mark.integration
class TestE2EAcceptance:
    """End-to-end acceptance scenarios through the real FastAPI app."""

    def test_happy_path_events_flow_through_app(
        self,
        bootstrap_env_all_healthy: None,
        postgres_container_sap: PostgresContainer,
        postgres_container_zup: PostgresContainer,
        ch_client,
    ) -> None:
        """Full pipeline: seed → app boot → poll → CH write → PG ack → /readyz counters."""
        run_async(_seed_container(postgres_container_sap, "sap"))
        run_async(_seed_container(postgres_container_zup, "zup"))
        create_destination_table(ch_client)

        app = create_app()
        with TestClient(app) as client:
            time.sleep(2.0)

            sources_in_ch = ch_source_names(ch_client)
            assert "sap" in sources_in_ch, f"sap rows missing from CH; found: {sources_in_ch}"
            assert "zup" in sources_in_ch, f"zup rows missing from CH; found: {sources_in_ch}"
            assert total_destination_rows(ch_client) == 4

            sap_flags = run_async(
                _query_processed_flags(postgres_container_sap, _SEED_ROW_IDS["sap"]),
            )
            for rid, processed in sap_flags.items():
                assert processed is True, f"sap row {rid} should be processed"

            zup_flags = run_async(
                _query_processed_flags(postgres_container_zup, _SEED_ROW_IDS["zup"]),
            )
            for rid, processed in zup_flags.items():
                assert processed is True, f"zup row {rid} should be processed"

            resp = client.get("/readyz")
            assert resp.status_code == 200
            body = resp.json()
            assert body["phase"] == "ready"
            assert body["ready"] is True
            assert body["clickhouse_writes"]["total_rows_written"] > 0
            assert body["acknowledgements"]["total_acknowledged"] > 0

    def test_no_duplicate_on_app_restart(
        self,
        bootstrap_env_all_healthy: None,
        postgres_container_sap: PostgresContainer,
        postgres_container_zup: PostgresContainer,
        ch_client,
    ) -> None:
        """Dedup token prevents double CH insert when the app is restarted and rows re-appear."""
        all_sap_ids = _SEED_ROW_IDS["sap"]
        all_zup_ids = _SEED_ROW_IDS["zup"]

        run_async(_seed_container(postgres_container_sap, "sap"))
        run_async(_seed_container(postgres_container_zup, "zup"))
        create_destination_table(ch_client)

        # First app boot
        app1 = create_app()
        with TestClient(app1):
            time.sleep(2.0)
            assert total_destination_rows(ch_client) == 4

        # Simulate re-processing pressure
        run_async(_reset_processed_flags(postgres_container_sap, all_sap_ids))
        run_async(_reset_processed_flags(postgres_container_zup, all_zup_ids))

        # Second app boot — dedup window prevents duplicates
        app2 = create_app()
        with TestClient(app2):
            time.sleep(2.0)
            assert total_destination_rows(ch_client) == 4

            sap_flags = run_async(
                _query_processed_flags(postgres_container_sap, all_sap_ids),
            )
            for rid, processed in sap_flags.items():
                assert processed is True, f"sap row {rid} not re-acknowledged after restart"

            zup_flags = run_async(
                _query_processed_flags(postgres_container_zup, all_zup_ids),
            )
            for rid, processed in zup_flags.items():
                assert processed is True, f"zup row {rid} not re-acknowledged after restart"

    def test_degraded_source_visible_in_readyz(
        self,
        bootstrap_env_with_bad_umts: None,
        postgres_container_sap: PostgresContainer,
        postgres_container_zup: PostgresContainer,
        ch_client,
    ) -> None:
        """One bad source doesn't block healthy sources and is visible in /readyz."""
        run_async(_seed_container(postgres_container_sap, "sap"))
        run_async(_seed_container(postgres_container_zup, "zup"))
        create_destination_table(ch_client)

        app = create_app()
        with TestClient(app) as client:
            time.sleep(3.0)

            resp = client.get("/readyz")
            assert resp.status_code == 503
            body = resp.json()
            assert body["phase"] == "degraded"
            assert body["ready"] is False
            assert "umts" in body["polling"]["last_failure_by_source"]

            sources_in_ch = ch_source_names(ch_client)
            assert "sap" in sources_in_ch
            assert "zup" in sources_in_ch

            sap_flags = run_async(
                _query_processed_flags(postgres_container_sap, _SEED_ROW_IDS["sap"]),
            )
            for rid, processed in sap_flags.items():
                assert processed is True, f"sap row {rid} should be processed"

            zup_flags = run_async(
                _query_processed_flags(postgres_container_zup, _SEED_ROW_IDS["zup"]),
            )
            for rid, processed in zup_flags.items():
                assert processed is True, f"zup row {rid} should be processed"

            health_resp = client.get("/healthz")
            assert health_resp.status_code == 200
            assert health_resp.json()["live"] is True

    def test_healthz_lifecycle(
        self,
        bootstrap_env_all_healthy: None,
    ) -> None:
        """Lifecycle: /healthz live+ready during runtime, phase=stopped after shutdown."""
        app = create_app()
        with TestClient(app) as client:
            resp = client.get("/healthz")
            assert resp.status_code == 200
            body = resp.json()
            assert body["live"] is True
            assert body["phase"] == "ready"

        assert app.state.runtime_state.phase.value == "stopped"
