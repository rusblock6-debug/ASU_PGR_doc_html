"""Tests for outbox record serialization (US-003)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from audit_lib.daemon.serialization import serialize_outbox_record


def _make_record(**overrides: Any) -> SimpleNamespace:
    """Build a fake AuditOutbox record with sensible defaults."""
    defaults: dict[str, Any] = {
        "id": uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
        "entity_type": "Order",
        "entity_id": "42",
        "operation": "create",
        "old_values": None,
        "new_values": {"amount": 100, "status": "new"},
        "user_id": "user-1",
        "timestamp": datetime(2025, 6, 15, 12, 30, 0, tzinfo=UTC),
        "service_name": "order-service",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestSerializeOutboxRecord:
    """Unit tests for serialize_outbox_record."""

    def test_returns_bytes(self) -> None:
        result = serialize_outbox_record(_make_record())
        assert isinstance(result, bytes)

    def test_valid_json(self) -> None:
        result = serialize_outbox_record(_make_record())
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_all_fields_present(self) -> None:
        data = json.loads(serialize_outbox_record(_make_record()))
        expected_keys = {
            "id",
            "entity_type",
            "entity_id",
            "operation",
            "old_values",
            "new_values",
            "user_id",
            "timestamp",
            "service_name",
        }
        assert set(data.keys()) == expected_keys

    def test_uuid_serialized_as_string(self) -> None:
        uid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        data = json.loads(serialize_outbox_record(_make_record(id=uid)))
        assert data["id"] == "12345678-1234-5678-1234-567812345678"
        assert isinstance(data["id"], str)

    def test_datetime_serialized_as_iso8601(self) -> None:
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        data = json.loads(serialize_outbox_record(_make_record(timestamp=dt)))
        assert data["timestamp"] == "2025-01-15T10:30:00+00:00"

    def test_jsonb_fields_as_dict(self) -> None:
        old = {"name": "old_name"}
        new = {"name": "new_name"}
        data = json.loads(
            serialize_outbox_record(_make_record(old_values=old, new_values=new))
        )
        assert data["old_values"] == {"name": "old_name"}
        assert data["new_values"] == {"name": "new_name"}

    def test_null_jsonb_fields(self) -> None:
        data = json.loads(
            serialize_outbox_record(
                _make_record(old_values=None, new_values=None)
            )
        )
        assert data["old_values"] is None
        assert data["new_values"] is None

    def test_null_optional_fields(self) -> None:
        data = json.loads(
            serialize_outbox_record(
                _make_record(user_id=None, service_name=None)
            )
        )
        assert data["user_id"] is None
        assert data["service_name"] is None

    def test_roundtrip_preserves_all_values(self) -> None:
        uid = uuid.uuid4()
        dt = datetime(2025, 3, 20, 8, 0, 0, tzinfo=UTC)
        old_vals = {"price": 10.5, "active": True}
        new_vals = {"price": 20.0, "active": False}

        record = _make_record(
            id=uid,
            entity_type="Product",
            entity_id="p-99",
            operation="update",
            old_values=old_vals,
            new_values=new_vals,
            user_id="admin",
            timestamp=dt,
            service_name="catalog",
        )

        data = json.loads(serialize_outbox_record(record))

        assert data["id"] == str(uid)
        assert data["entity_type"] == "Product"
        assert data["entity_id"] == "p-99"
        assert data["operation"] == "update"
        assert data["old_values"] == old_vals
        assert data["new_values"] == new_vals
        assert data["user_id"] == "admin"
        assert data["timestamp"] == dt.isoformat()
        assert data["service_name"] == "catalog"

    def test_utf8_encoding(self) -> None:
        record = _make_record(entity_type="Заказ", service_name="сервис")
        raw = serialize_outbox_record(record)
        data = json.loads(raw.decode("utf-8"))
        assert data["entity_type"] == "Заказ"
        assert data["service_name"] == "сервис"
