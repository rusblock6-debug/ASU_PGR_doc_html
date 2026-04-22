"""Serialize outbox records to JSON bytes for RabbitMQ Stream publishing."""

from __future__ import annotations

import json
from typing import Any

from audit_lib.serializers import default_serializer


def serialize_outbox_record(record: Any) -> bytes:
    """Serialize an AuditOutbox record to JSON bytes.

    Extracts all audit fields from the record and produces a compact
    JSON payload suitable for publishing to RabbitMQ Stream.

    Uses :func:`audit_lib.serializers.default_serializer` as the
    ``default`` handler for :func:`json.dumps`, so UUID, datetime,
    Decimal and other non-native types are converted automatically.

    Parameters
    ----------
    record:
        An ``AuditOutbox`` model instance (or any object with the
        expected audit outbox attributes).

    Returns
    -------
    bytes
        UTF-8 encoded JSON.
    """
    payload: dict[str, Any] = {
        "id": record.id,
        "entity_type": record.entity_type,
        "entity_id": record.entity_id,
        "operation": record.operation,
        "old_values": record.old_values,
        "new_values": record.new_values,
        "user_id": record.user_id,
        "timestamp": record.timestamp,
        "service_name": record.service_name,
    }
    return json.dumps(payload, default=default_serializer).encode("utf-8")
