"""Structured JSON logging bootstrap for the API gateway."""

from __future__ import annotations

import json
import logging
import math
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

_REDACTED_VALUE = "[REDACTED]"
_MAX_SERIALIZE_DEPTH = 8
_SENSITIVE_KEY_PARTS = (
    "authorization",
    "token",
    "secret",
    "password",
    "api_key",
)
_RESERVED_LOG_RECORD_FIELDS = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "taskName",
        "message",
        "asctime",
    },
)


def _utc_timestamp(created: float | None = None) -> str:
    """Return UTC RFC3339 timestamp with milliseconds."""
    instant = datetime.fromtimestamp(created, UTC) if created else datetime.now(UTC)
    return instant.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _safe_repr(value: object) -> str:
    """Return repr(value) without raising."""
    try:
        return repr(value)
    except Exception:
        return f"<unrepresentable {type(value).__name__}>"


def _is_sensitive_key(key: str) -> bool:
    """Return True when key likely contains secret-bearing data."""
    normalized = key.strip().lower().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _sanitize_for_json(
    value: Any,
    *,
    field_name: str | None = None,
    depth: int = 0,
) -> Any:
    """Convert arbitrary Python objects to safe JSON-serializable values."""
    if field_name and _is_sensitive_key(field_name):
        return _REDACTED_VALUE

    if depth > _MAX_SERIALIZE_DEPTH:
        return _safe_repr(value)

    if value is None or isinstance(value, bool | int | str):
        return value

    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    if isinstance(value, datetime):
        timestamp = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return (
            timestamp.astimezone(UTC)
            .isoformat(timespec="milliseconds")
            .replace(
                "+00:00",
                "Z",
            )
        )

    if isinstance(value, BaseException):
        return {"type": type(value).__name__, "message": str(value)}

    if isinstance(value, Mapping):
        return {
            str(key): _sanitize_for_json(item, field_name=str(key), depth=depth + 1)
            for key, item in value.items()
        }

    if isinstance(value, list | tuple | set | frozenset):
        return [_sanitize_for_json(item, depth=depth + 1) for item in value]

    return _safe_repr(value)


def _resolve_log_level(log_level: str) -> int:
    """Resolve textual log level, defaulting to INFO when invalid."""
    level_name = log_level.strip().upper()
    return logging.getLevelNamesMapping().get(level_name, logging.INFO)


class _MaxLevelFilter(logging.Filter):
    """Allow records up to and including a maximum level."""

    def __init__(self, max_level: int) -> None:
        super().__init__()
        self._max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        """Return True for levels <= configured maximum."""
        return record.levelno <= self._max_level


class JsonFormatter(logging.Formatter):
    """Format records as single-line JSON with safe serialization."""

    def __init__(self, static_fields: Mapping[str, Any] | None = None) -> None:
        super().__init__()
        source_fields = static_fields or {}
        self._static_fields = {
            str(key): _sanitize_for_json(value, field_name=str(key))
            for key, value in source_fields.items()
        }

    def format(self, record: logging.LogRecord) -> str:
        """Return a JSON string and never raise serialization errors."""
        try:
            payload = self._build_payload(record)
            return json.dumps(
                payload,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
        except Exception as exc:
            fallback_payload = {
                "timestamp": _utc_timestamp(),
                "level": "error",
                "message": "log_serialization_failed",
                **self._static_fields,
                "original_logger": record.name,
                "original_level": record.levelname.lower(),
                "serialization_error": _safe_repr(exc),
                "original_message": _safe_repr(record.msg),
            }
            return json.dumps(
                fallback_payload,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )

    def _build_payload(self, record: logging.LogRecord) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "timestamp": _utc_timestamp(record.created),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            **self._static_fields,
        }

        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_FIELDS or key.startswith("_"):
                continue
            payload[key] = _sanitize_for_json(value, field_name=key)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        if record.stack_info:
            payload["stack_info"] = str(record.stack_info)

        return payload


def configure_logging(
    *,
    service_name: str,
    environment: str | None = None,
    log_level: str = "INFO",
) -> None:
    """Configure process-wide JSON logging to stdout/stderr."""
    static_context: dict[str, Any] = {"service_name": service_name}
    if environment:
        static_context["environment"] = environment

    formatter = JsonFormatter(static_fields=static_context)

    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(_MaxLevelFilter(logging.WARNING))
    stdout_handler.setFormatter(formatter)

    stderr_handler = logging.StreamHandler(stream=sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(_resolve_log_level(log_level))
    root_logger.propagate = False
    root_logger.addHandler(stdout_handler)
    root_logger.addHandler(stderr_handler)
