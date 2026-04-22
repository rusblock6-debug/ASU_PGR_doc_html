"""Нормализация входящих сообщений RabbitMQ."""

import json
from typing import Any


def _normalize_null_strings(value: Any) -> Any:
    """Рекурсивно приводит строковый 'null' к None."""
    if isinstance(value, dict):
        return {key: _normalize_null_strings(item) for key, item in value.items()}

    if isinstance(value, list):
        return [_normalize_null_strings(item) for item in value]

    if isinstance(value, str) and value.strip().lower() == "null":
        return None

    return value


def normalize_message_payload(raw_msg: Any) -> dict[str, Any] | None:
    """Нормализует входящий payload к словарю."""
    if isinstance(raw_msg, dict):
        return _normalize_null_strings(raw_msg)

    if isinstance(raw_msg, bytes):
        if not raw_msg:
            return None
        try:
            decoded = raw_msg.decode("utf-8").strip()
        except UnicodeDecodeError:
            return None
        if not decoded:
            return None
        try:
            parsed = json.loads(decoded)
        except json.JSONDecodeError:
            return None
        return _normalize_null_strings(parsed) if isinstance(parsed, dict) else None

    if isinstance(raw_msg, str):
        stripped = raw_msg.strip()
        if not stripped:
            return None
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return None
        return _normalize_null_strings(parsed) if isinstance(parsed, dict) else None

    return None
