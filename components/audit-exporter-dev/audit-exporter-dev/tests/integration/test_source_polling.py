"""Integration tests for ordered source polling and canonical export mapping."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from src.core.config import AppSettings, SourceName
from tests.integration.conftest import (
    build_runtime_state,
    connect_to_source,
    seed_audit_outbox,
)

# Seed data — inserted out of order to prove ordering

_ROW_1 = (
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
)
_ROW_2 = (
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
)
_ROW_3 = (
    UUID("00000000-0000-0000-0000-000000000003"),
    "invoice",
    "inv-3",
    "update",
    '{"status": "draft"}',
    '{"status": "approved"}',
    "user-3",
    datetime(2026, 3, 17, 12, 5, tzinfo=UTC),
    False,
    "sap-service",
)
_ROW_4_PROCESSED = (
    UUID("00000000-0000-0000-0000-000000000004"),
    "invoice",
    "inv-4",
    "delete",
    '{"status": "cancelled"}',
    None,
    "user-4",
    datetime(2026, 3, 17, 12, 10, tzinfo=UTC),
    True,
    "sap-service",
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_source_reader_returns_ordered_unprocessed_events_without_acknowledgement(
    bootstrap_env_sap_ch: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Override batch size to 2 for this test
    monkeypatch.setenv("SOURCE_POLL_BATCH_SIZE", "2")

    settings = AppSettings()
    state = build_runtime_state(settings)
    reader = state.postgres_readers[SourceName.sap]

    # Seed rows deliberately out of timestamp/id order
    admin = await connect_to_source(settings, SourceName.sap)
    try:
        await seed_audit_outbox(admin, [_ROW_3, _ROW_2, _ROW_1, _ROW_4_PROCESSED])

        exported_events, poll_result = await reader.poll(
            batch_size=settings.source_poll_batch_size,
        )
        state.record_source_poll_success(poll_result)

        # Should return first 2 unprocessed rows in timestamp+id order
        assert [e.outbox_id for e in exported_events] == [
            UUID("00000000-0000-0000-0000-000000000001"),
            UUID("00000000-0000-0000-0000-000000000002"),
        ]
        assert all(e.source_name is SourceName.sap for e in exported_events)
        assert exported_events[0].entity_type == "invoice"
        assert exported_events[0].service_name == "sap-service"
        assert exported_events[0].new_values == {"status": "new"}
        assert exported_events[1].old_values == {"status": "new"}

        assert poll_result.source_name is SourceName.sap
        assert poll_result.batch_size == 2
        assert poll_result.row_count == 2
        assert poll_result.highest_seen_timestamp == datetime(2026, 3, 17, 12, 0, tzinfo=UTC)
        assert poll_result.highest_seen_outbox_id == UUID("00000000-0000-0000-0000-000000000002")

        assert state.polling is not None
        assert state.polling.configured_batch_size == 2
        assert state.polling.readers == [SourceName.sap]
        assert state.polling.last_success_by_source[SourceName.sap].row_count == 2
        assert state.polling.last_failure_by_source == {}

        # Verify polling did NOT acknowledge rows
        rows = await admin.fetch(
            "SELECT id, processed FROM audit_outbox ORDER BY timestamp ASC, id ASC",
        )
        assert [(str(row["id"]), row["processed"]) for row in rows] == [
            ("00000000-0000-0000-0000-000000000001", False),
            ("00000000-0000-0000-0000-000000000002", False),
            ("00000000-0000-0000-0000-000000000003", False),
            ("00000000-0000-0000-0000-000000000004", True),
        ]
    finally:
        await admin.close()
        await reader.close()
