"""Integration tests proving multi-source isolation, readiness degradation, and recovery."""

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest

from src.clickhouse.client import ClickHouseClient
from src.core.config import AppSettings, SourceName
from src.core.orchestrator import run_polling_loop
from src.core.state import AppLifecyclePhase
from tests.integration.conftest import (
    build_runtime_state,
    ch_source_names,
    connect_to_source,
    create_destination_table,
    seed_audit_outbox,
)

# Seed data per source

_SEED_ROW_IDS: dict[str, list[UUID]] = {
    "sap": [
        UUID("a0000000-0000-0000-0000-000000000001"),
        UUID("a0000000-0000-0000-0000-000000000002"),
    ],
    "zup": [
        UUID("b0000000-0000-0000-0000-000000000001"),
        UUID("b0000000-0000-0000-0000-000000000002"),
    ],
    "umts": [
        UUID("c0000000-0000-0000-0000-000000000001"),
        UUID("c0000000-0000-0000-0000-000000000002"),
    ],
}


def _make_seed_rows(source_name: str, row_ids: list[UUID]) -> list[tuple]:
    """Build seed row tuples for a given source."""
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


async def _run_n_cycles(
    state,
    n: int,
    interval: float,
) -> None:
    """Run the orchestrator loop for exactly *n* cycles then cancel it."""
    task = asyncio.create_task(run_polling_loop(state, interval))
    margin = 4.0  # generous: umts may take up to 2 s to time out
    await asyncio.sleep(n * interval + margin)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# Tests


@pytest.mark.integration
@pytest.mark.asyncio
async def test_healthy_sources_processed_while_bad_source_fails(
    bootstrap_env_with_bad_umts: None,
    ch_client,
) -> None:
    """Sap and zup rows are exported to CH even though umts fails every cycle."""
    settings = AppSettings()
    create_destination_table(ch_client)

    admin_sap = await connect_to_source(settings, SourceName.sap)
    admin_zup = await connect_to_source(settings, SourceName.zup)
    await seed_audit_outbox(admin_sap, _make_seed_rows("sap", _SEED_ROW_IDS["sap"]))
    await seed_audit_outbox(admin_zup, _make_seed_rows("zup", _SEED_ROW_IDS["zup"]))

    ch_writer = ClickHouseClient(settings=settings.clickhouse(), client=ch_client)
    state = build_runtime_state(
        settings,
        ch_writer,
        sources={SourceName.sap: True, SourceName.zup: True, SourceName.umts: False},
    )

    try:
        await _run_n_cycles(state, n=1, interval=0.1)

        names_in_ch = ch_source_names(ch_client)
        assert "sap" in names_in_ch, "sap rows should be in CH"
        assert "zup" in names_in_ch, "zup rows should be in CH"
        assert "umts" not in names_in_ch, "umts rows must NOT be in CH"

        sap_rows = await admin_sap.fetch(
            "SELECT id, processed FROM audit_outbox ORDER BY id",
        )
        for row in sap_rows:
            assert row["processed"] is True, f"sap row {row['id']} should be processed"

        zup_rows = await admin_zup.fetch(
            "SELECT id, processed FROM audit_outbox ORDER BY id",
        )
        for row in zup_rows:
            assert row["processed"] is True, f"zup row {row['id']} should be processed"

        assert state.polling is not None
        assert SourceName.umts in state.polling.last_failure_by_source
    finally:
        await admin_sap.close()
        await admin_zup.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_readyz_reflects_degraded_phase_on_source_failure(
    bootstrap_env_with_bad_umts: None,
    ch_client,
) -> None:
    """/readyz payload shows phase=degraded with per-source failure detail after umts fails."""
    settings = AppSettings()
    create_destination_table(ch_client)
    admin_sap = await connect_to_source(settings, SourceName.sap)
    await seed_audit_outbox(admin_sap, _make_seed_rows("sap", _SEED_ROW_IDS["sap"]))

    ch_writer = ClickHouseClient(settings=settings.clickhouse(), client=ch_client)
    state = build_runtime_state(
        settings,
        ch_writer,
        sources={SourceName.sap: True, SourceName.zup: True, SourceName.umts: False},
    )

    try:
        await _run_n_cycles(state, n=1, interval=0.1)

        payload = state.readiness_payload()
        assert payload["phase"] == "degraded", f"Expected degraded, got {payload['phase']}"
        assert payload["ready"] is False

        polling_data = payload["polling"]
        assert isinstance(polling_data, dict)
        failures = polling_data["last_failure_by_source"]
        assert "umts" in failures, f"Expected umts in failures, got: {failures}"
        assert failures["umts"], "umts failure message should be non-empty"
    finally:
        await admin_sap.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_recovery_clears_degraded_state(
    bootstrap_env_all_healthy: None,
    ch_client,
) -> None:
    """When all sources are healthy, phase is ready and no failures are recorded."""
    settings = AppSettings()
    create_destination_table(ch_client)

    admin_sap = await connect_to_source(settings, SourceName.sap)
    admin_zup = await connect_to_source(settings, SourceName.zup)
    admin_umts = await connect_to_source(settings, SourceName.umts)
    await seed_audit_outbox(admin_sap, _make_seed_rows("sap", _SEED_ROW_IDS["sap"]))
    await seed_audit_outbox(admin_zup, _make_seed_rows("zup", _SEED_ROW_IDS["zup"]))
    await seed_audit_outbox(admin_umts, _make_seed_rows("umts", _SEED_ROW_IDS["umts"]))

    ch_writer = ClickHouseClient(settings=settings.clickhouse(), client=ch_client)
    state = build_runtime_state(
        settings,
        ch_writer,
        sources={SourceName.sap: True, SourceName.zup: True, SourceName.umts: True},
    )

    try:
        await _run_n_cycles(state, n=1, interval=0.1)

        assert state.phase == AppLifecyclePhase.ready
        assert state.polling is not None
        assert len(state.polling.last_failure_by_source) == 0, (
            f"Expected no poll failures, got: {state.polling.last_failure_by_source}"
        )

        payload = state.readiness_payload()
        assert payload["phase"] == "ready"
        assert payload["ready"] is True
    finally:
        await admin_sap.close()
        await admin_zup.close()
        await admin_umts.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_per_source_log_lines_emitted(
    bootstrap_env_with_bad_umts: None,
    ch_client,
) -> None:
    """Structured log lines identify which source succeeded and which failed."""
    from loguru import logger

    settings = AppSettings()
    create_destination_table(ch_client)
    admin_sap = await connect_to_source(settings, SourceName.sap)
    await seed_audit_outbox(admin_sap, _make_seed_rows("sap", _SEED_ROW_IDS["sap"]))

    ch_writer = ClickHouseClient(settings=settings.clickhouse(), client=ch_client)
    state = build_runtime_state(
        settings,
        ch_writer,
        sources={SourceName.sap: True, SourceName.zup: True, SourceName.umts: False},
    )

    captured_messages: list[str] = []
    sink_id = logger.add(lambda msg: captured_messages.append(msg.record["message"]), level="INFO")

    try:
        await _run_n_cycles(state, n=1, interval=0.1)

        assert any("source_cycle_complete" in m for m in captured_messages), (
            f"Expected source_cycle_complete log. Got: {captured_messages[:10]}"
        )
        assert any("source_cycle_failed" in m for m in captured_messages), (
            f"Expected source_cycle_failed log. Got: {captured_messages[:10]}"
        )
        assert any("cycle_end" in m for m in captured_messages), "Expected cycle_end log line"
    finally:
        logger.remove(sink_id)
        await admin_sap.close()
