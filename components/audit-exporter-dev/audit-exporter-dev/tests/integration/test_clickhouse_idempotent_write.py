"""Integration test: duplicate-safe ClickHouse writer with idempotent retries.

Proves that writing the same exported event batch twice through the public
``ClickHouseClient.insert_exported_events`` path results in exactly one
destination row per ``(source_name, outbox_id)`` pair.
"""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from src.clickhouse.client import DESTINATION_TABLE, ClickHouseClient, derive_dedup_token
from src.core.config import AppSettings, SourceName
from src.db.source_connections import ExportedAuditEvent, build_postgres_reader
from tests.integration.conftest import (
    build_runtime_state,
    connect_to_source,
    create_destination_table,
    seed_audit_outbox,
    total_destination_rows,
)

# Sample events

_SAMPLE_EVENTS = [
    ExportedAuditEvent(
        source_name=SourceName.sap,
        outbox_id=UUID("00000000-0000-0000-0000-000000000001"),
        entity_type="invoice",
        entity_id="inv-1",
        operation="insert",
        old_values=None,
        new_values={"status": "new"},
        user_id="user-1",
        timestamp=datetime(2026, 3, 17, 12, 0, 0, tzinfo=UTC),
        service_name="sap-service",
    ),
    ExportedAuditEvent(
        source_name=SourceName.sap,
        outbox_id=UUID("00000000-0000-0000-0000-000000000002"),
        entity_type="invoice",
        entity_id="inv-2",
        operation="update",
        old_values={"status": "new"},
        new_values={"status": "draft"},
        user_id="user-2",
        timestamp=datetime(2026, 3, 17, 12, 0, 0, tzinfo=UTC),
        service_name="sap-service",
    ),
]


# Tests


@pytest.mark.integration
@pytest.mark.asyncio
async def test_idempotent_write_produces_exactly_one_row_per_event(
    bootstrap_env_sap_ch: None,
    ch_client,
) -> None:
    """Write the same batch twice; assert one row per source event identity."""
    create_destination_table(ch_client)
    settings = AppSettings()
    writer = ClickHouseClient(settings=settings.clickhouse(), client=ch_client)

    outcome_1 = await writer.insert_exported_events(_SAMPLE_EVENTS)
    assert outcome_1.ok is True
    assert outcome_1.row_count == 2
    assert outcome_1.dedup_token != ""

    outcome_2 = await writer.insert_exported_events(_SAMPLE_EVENTS)
    assert outcome_2.ok is True
    assert outcome_2.dedup_token == outcome_1.dedup_token

    for event in _SAMPLE_EVENTS:
        count = int(
            ch_client.command(
                f"SELECT count() FROM {DESTINATION_TABLE} "  # noqa: S608
                f"WHERE source_name = '{event.source_name.value}' "
                f"AND outbox_id = '{event.outbox_id}'",
            ),
        )
        assert count == 1, (
            f"Expected 1 row for ({event.source_name}, {event.outbox_id}), got {count}"
        )

    assert total_destination_rows(ch_client) == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_empty_batch_write_succeeds_with_zero_rows(
    bootstrap_env_sap_ch: None,
    ch_client,
) -> None:
    """Empty event list should succeed with row_count=0 and no ClickHouse call."""
    create_destination_table(ch_client)
    settings = AppSettings()
    writer = ClickHouseClient(settings=settings.clickhouse(), client=ch_client)

    outcome = await writer.insert_exported_events([])
    assert outcome.ok is True
    assert outcome.row_count == 0
    assert outcome.dedup_token == ""
    assert total_destination_rows(ch_client) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_write_outcome_is_recorded_on_runtime_state(
    bootstrap_env_sap_ch: None,
    ch_client,
) -> None:
    """Verify runtime state records write outcomes for observability."""
    create_destination_table(ch_client)
    settings = AppSettings()
    writer = ClickHouseClient(settings=settings.clickhouse(), client=ch_client)
    state = build_runtime_state(settings, writer)

    outcome = await writer.insert_exported_events(_SAMPLE_EVENTS)
    state.record_clickhouse_write(outcome)

    assert state.clickhouse_writes is not None
    assert state.clickhouse_writes.total_writes == 1
    assert state.clickhouse_writes.total_rows_written == 2
    assert state.clickhouse_writes.last_success is not None
    assert state.clickhouse_writes.last_success.ok is True
    assert state.clickhouse_writes.last_failure is None
    assert state.clickhouse_writes.updated_at is not None

    await state.postgres_readers[SourceName.sap].close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_source_processed_flags_unchanged_after_write(
    bootstrap_env_sap_ch: None,
    ch_client,
) -> None:
    """S02 does not acknowledge source rows — processed flags must stay false."""
    create_destination_table(ch_client)
    settings = AppSettings()

    admin = await connect_to_source(settings, SourceName.sap)
    try:
        await seed_audit_outbox(
            admin,
            [
                (
                    UUID("00000000-0000-0000-0000-000000000001"),
                    "invoice",
                    "inv-1",
                    "insert",
                    None,
                    '{"status": "new"}',
                    "user-1",
                    datetime(2026, 3, 17, 12, 0, tzinfo=UTC),
                    False,
                    "sap-service",
                ),
                (
                    UUID("00000000-0000-0000-0000-000000000002"),
                    "invoice",
                    "inv-2",
                    "update",
                    '{"status": "new"}',
                    '{"status": "draft"}',
                    "user-2",
                    datetime(2026, 3, 17, 12, 0, tzinfo=UTC),
                    False,
                    "sap-service",
                ),
            ],
        )

        reader = build_postgres_reader(settings.postgres_sources()[SourceName.sap])
        events = await reader.fetch_export_batch(batch_size=10)
        assert len(events) == 2

        writer = ClickHouseClient(settings=settings.clickhouse(), client=ch_client)
        outcome = await writer.insert_exported_events(events)
        assert outcome.ok is True

        rows = await admin.fetch(
            "SELECT id, processed FROM audit_outbox ORDER BY id",
        )
        for row in rows:
            assert row["processed"] is False, f"Source row {row['id']} should still be unprocessed"

        assert total_destination_rows(ch_client) == 2
        await reader.close()
    finally:
        await admin.close()


@pytest.mark.integration
def test_dedup_token_is_deterministic() -> None:
    """Token from the same identities (in any order) must be identical."""
    reversed_events = list(reversed(_SAMPLE_EVENTS))
    assert derive_dedup_token(_SAMPLE_EVENTS) == derive_dedup_token(reversed_events)
    assert derive_dedup_token(_SAMPLE_EVENTS) != ""
