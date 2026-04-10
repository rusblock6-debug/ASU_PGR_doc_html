"""Integration tests for source row acknowledgement, observability, and pipeline composition."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from src.clickhouse.client import ClickHouseClient
from src.core.config import AppSettings, SourceName
from src.core.pipeline import process_source
from src.db.source_connections import AcknowledgementOutcome, build_postgres_reader
from tests.integration.conftest import (
    build_runtime_state,
    connect_to_source,
    create_destination_table,
    seed_audit_outbox,
    total_destination_rows,
)

# Shared seed data

_ROW_1_ID = UUID("00000000-0000-0000-0000-000000000001")
_ROW_2_ID = UUID("00000000-0000-0000-0000-000000000002")
_ROW_3_ID = UUID("00000000-0000-0000-0000-000000000003")
_ROW_4_ID = UUID("00000000-0000-0000-0000-000000000004")

_ACK_SEED_ROWS = [
    (
        _ROW_1_ID,
        "invoice",
        "inv-1",
        "insert",
        None,
        '{"status":"new"}',
        "user-1",
        datetime(2026, 3, 17, 12, 0, tzinfo=UTC),
        False,
        "sap-service",
    ),
    (
        _ROW_2_ID,
        "invoice",
        "inv-2",
        "update",
        '{"status":"new"}',
        '{"status":"draft"}',
        "user-2",
        datetime(2026, 3, 17, 12, 1, tzinfo=UTC),
        False,
        "sap-service",
    ),
    (
        _ROW_3_ID,
        "invoice",
        "inv-3",
        "update",
        '{"status":"draft"}',
        '{"status":"approved"}',
        "user-3",
        datetime(2026, 3, 17, 12, 2, tzinfo=UTC),
        False,
        "sap-service",
    ),
    (
        _ROW_4_ID,
        "invoice",
        "inv-4",
        "delete",
        '{"status":"cancelled"}',
        None,
        "user-4",
        datetime(2026, 3, 17, 12, 3, tzinfo=UTC),
        True,
        "sap-service",
    ),
]

_PIPELINE_ROW_1_ID = UUID("10000000-0000-0000-0000-000000000001")
_PIPELINE_ROW_2_ID = UUID("10000000-0000-0000-0000-000000000002")

_PIPELINE_SEED_ROWS = [
    (
        _PIPELINE_ROW_1_ID,
        "invoice",
        "inv-p1",
        "insert",
        None,
        '{"status":"new"}',
        "user-p1",
        datetime(2026, 3, 17, 14, 0, tzinfo=UTC),
        False,
        "sap-service",
    ),
    (
        _PIPELINE_ROW_2_ID,
        "invoice",
        "inv-p2",
        "update",
        '{"status":"new"}',
        '{"status":"draft"}',
        "user-p2",
        datetime(2026, 3, 17, 14, 1, tzinfo=UTC),
        False,
        "sap-service",
    ),
]


# Acknowledgement tests


@pytest.mark.integration
@pytest.mark.asyncio
async def test_acknowledge_marks_only_specified_rows_processed(
    bootstrap_env_sap_ch: None,
) -> None:
    """Acknowledging 2 of 3 unprocessed rows leaves the third untouched."""
    settings = AppSettings()
    admin = await connect_to_source(settings, SourceName.sap)
    await seed_audit_outbox(admin, _ACK_SEED_ROWS)
    reader = build_postgres_reader(settings.postgres_sources()[SourceName.sap])

    try:
        outcome = await reader.acknowledge_rows([_ROW_1_ID, _ROW_2_ID])

        assert outcome.ok is True
        assert outcome.acknowledged_count == 2
        assert outcome.source_name is SourceName.sap
        assert outcome.error_message is None
        assert outcome.acknowledged_at is not None

        rows = await admin.fetch(
            "SELECT id, processed FROM audit_outbox ORDER BY timestamp ASC, id ASC",
        )
        processed_map = {row["id"]: row["processed"] for row in rows}
        assert processed_map[_ROW_1_ID] is True
        assert processed_map[_ROW_2_ID] is True
        assert processed_map[_ROW_3_ID] is False
        assert processed_map[_ROW_4_ID] is True  # was already processed
    finally:
        await admin.close()
        await reader.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_acknowledge_empty_list_is_noop(
    bootstrap_env_sap_ch: None,
) -> None:
    """Acknowledging an empty list succeeds with zero count and no side effects."""
    settings = AppSettings()
    admin = await connect_to_source(settings, SourceName.sap)
    await seed_audit_outbox(admin, _ACK_SEED_ROWS)
    reader = build_postgres_reader(settings.postgres_sources()[SourceName.sap])

    try:
        outcome = await reader.acknowledge_rows([])

        assert outcome.ok is True
        assert outcome.acknowledged_count == 0

        rows = await admin.fetch(
            "SELECT id, processed FROM audit_outbox ORDER BY timestamp ASC, id ASC",
        )
        processed_map = {row["id"]: row["processed"] for row in rows}
        assert processed_map[_ROW_1_ID] is False
        assert processed_map[_ROW_2_ID] is False
        assert processed_map[_ROW_3_ID] is False
        assert processed_map[_ROW_4_ID] is True
    finally:
        await admin.close()
        await reader.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_acknowledgement_outcome_recorded_on_runtime_state(
    bootstrap_env_sap_ch: None,
) -> None:
    """``record_acknowledgement()`` updates the AcknowledgementSnapshot on runtime state."""
    settings = AppSettings()
    state = build_runtime_state(settings)

    success_outcome = AcknowledgementOutcome(
        source_name=SourceName.sap,
        acknowledged_count=5,
        ok=True,
        error_message=None,
        acknowledged_at=datetime(2026, 3, 17, 12, 0, tzinfo=UTC),
    )
    state.record_acknowledgement(success_outcome)

    assert state.acknowledgements is not None
    assert state.acknowledgements.total_acknowledged == 5
    assert state.acknowledgements.last_success_by_source[SourceName.sap] == success_outcome
    assert SourceName.sap not in state.acknowledgements.last_failure_by_source
    assert state.acknowledgements.updated_at is not None

    payload = state.readiness_payload()
    assert "acknowledgements" in payload
    ack_payload = payload["acknowledgements"]
    assert isinstance(ack_payload, dict)
    assert ack_payload["total_acknowledged"] == 5
    assert ack_payload["updated_at"] is not None

    failure_outcome = AcknowledgementOutcome(
        source_name=SourceName.sap,
        acknowledged_count=0,
        ok=False,
        error_message="connection refused [credentials redacted: ***]",
        acknowledged_at=datetime(2026, 3, 17, 12, 5, tzinfo=UTC),
    )
    state.record_acknowledgement(failure_outcome)

    assert state.acknowledgements.last_failure_by_source[SourceName.sap] == (
        "connection refused [credentials redacted: ***]"
    )
    assert state.acknowledgements.total_acknowledged == 5  # unchanged on failure

    await state.postgres_readers[SourceName.sap].close()


# Pipeline composition tests (poll → write → ack)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_process_source_happy_path(
    bootstrap_env_sap_ch: None,
    ch_client,
) -> None:
    """Full poll → write → ack cycle succeeds: CH has rows, source rows are processed."""
    create_destination_table(ch_client)
    settings = AppSettings()
    admin = await connect_to_source(settings, SourceName.sap)
    await seed_audit_outbox(admin, _PIPELINE_SEED_ROWS)

    ch_writer = ClickHouseClient(settings=settings.clickhouse(), client=ch_client)
    state = build_runtime_state(settings, ch_writer)
    reader = state.postgres_readers[SourceName.sap]

    try:
        result = await process_source(reader, ch_writer, batch_size=10, state=state)

        assert result.phase_reached == "completed"
        assert result.source_name is SourceName.sap
        assert result.poll_result is not None
        assert result.poll_result.row_count == 2
        assert result.write_outcome is not None
        assert result.write_outcome.ok is True
        assert result.ack_outcome is not None
        assert result.ack_outcome.ok is True
        assert result.ack_outcome.acknowledged_count == 2

        assert total_destination_rows(ch_client) == 2

        rows = await admin.fetch(
            "SELECT id, processed FROM audit_outbox ORDER BY timestamp ASC, id ASC",
        )
        for row in rows:
            assert row["processed"] is True, f"Row {row['id']} should be processed"

        assert state.acknowledgements is not None
        assert state.acknowledgements.total_acknowledged == 2
        assert SourceName.sap in state.acknowledgements.last_success_by_source
    finally:
        await admin.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_process_source_ch_failure_no_ack(
    bootstrap_env_sap_ch: None,
    ch_client,
) -> None:
    """When CH write fails, source rows stay unprocessed and no ack happens."""
    settings = AppSettings()
    admin = await connect_to_source(settings, SourceName.sap)
    await seed_audit_outbox(admin, _PIPELINE_SEED_ROWS)

    ch_writer = ClickHouseClient(settings=settings.clickhouse(), client=ch_client)
    state = build_runtime_state(settings, ch_writer)
    reader = state.postgres_readers[SourceName.sap]

    # Drop destination table so write fails
    from src.clickhouse.client import DESTINATION_TABLE

    ch_client.command(f"DROP TABLE IF EXISTS {DESTINATION_TABLE}")

    try:
        result = await process_source(reader, ch_writer, batch_size=10, state=state)

        assert result.phase_reached == "write_failed"
        assert result.write_outcome is not None
        assert result.write_outcome.ok is False
        assert result.ack_outcome is None

        rows = await admin.fetch(
            "SELECT id, processed FROM audit_outbox ORDER BY timestamp ASC, id ASC",
        )
        for row in rows:
            assert row["processed"] is False, (
                f"Row {row['id']} must stay unprocessed after CH failure"
            )
    finally:
        await admin.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_process_source_crash_between_write_and_ack_recovery(
    bootstrap_env_sap_ch: None,
    ch_client,
) -> None:
    """Simulate crash after CH write but before ack: retry deduplicates and then acks."""
    create_destination_table(ch_client)
    settings = AppSettings()
    admin = await connect_to_source(settings, SourceName.sap)
    await seed_audit_outbox(admin, _PIPELINE_SEED_ROWS)

    reader = build_postgres_reader(settings.postgres_sources()[SourceName.sap])
    ch_writer = ClickHouseClient(settings=settings.clickhouse(), client=ch_client)

    try:
        # Partial cycle: poll + write, then "crash" (skip ack)
        events, _poll_result = await reader.poll(batch_size=10)
        assert len(events) == 2

        write_outcome = await ch_writer.insert_exported_events(events)
        assert write_outcome.ok is True

        # Source rows still unprocessed, CH has the rows
        rows = await admin.fetch(
            "SELECT id, processed FROM audit_outbox ORDER BY timestamp ASC, id ASC",
        )
        for row in rows:
            assert row["processed"] is False

        assert total_destination_rows(ch_client) == 2

        # Full retry: re-polls same rows, re-writes (deduped), acks
        state = build_runtime_state(settings, ch_writer)
        retry_reader = state.postgres_readers[SourceName.sap]

        result = await process_source(retry_reader, ch_writer, batch_size=10, state=state)

        assert result.phase_reached == "completed"
        assert result.write_outcome is not None
        assert result.write_outcome.ok is True
        assert result.ack_outcome is not None
        assert result.ack_outcome.ok is True

        # Dedup prevented duplicates
        assert total_destination_rows(ch_client) == 2

        rows = await admin.fetch(
            "SELECT id, processed FROM audit_outbox ORDER BY timestamp ASC, id ASC",
        )
        for row in rows:
            assert row["processed"] is True, f"Row {row['id']} should be processed after retry"
    finally:
        await admin.close()
        await reader.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_process_source_empty_poll_short_circuits(
    bootstrap_env_sap_ch: None,
    ch_client,
) -> None:
    """Empty poll returns poll_empty with no write or ack attempted."""
    create_destination_table(ch_client)
    settings = AppSettings()
    admin = await connect_to_source(settings, SourceName.sap)
    await seed_audit_outbox(admin, [])  # empty table

    ch_writer = ClickHouseClient(settings=settings.clickhouse(), client=ch_client)
    state = build_runtime_state(settings, ch_writer)
    reader = state.postgres_readers[SourceName.sap]

    try:
        result = await process_source(reader, ch_writer, batch_size=10, state=state)

        assert result.phase_reached == "poll_empty"
        assert result.poll_result is not None
        assert result.poll_result.row_count == 0
        assert result.write_outcome is None
        assert result.ack_outcome is None

        assert total_destination_rows(ch_client) == 0
    finally:
        await admin.close()
