"""Чтение веса ТС из Redis (стримы telemetry-service:weight:{vehicle_id})."""

from __future__ import annotations

import ast
import json
import logging
from typing import Any

from redis.exceptions import ResponseError

from app.utils.redis import cache

logger = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "telemetry-service:weight:"


def redis_key(vehicle_id: str | int) -> str:
    return f"{REDIS_KEY_PREFIX}{vehicle_id}"


def _read_last_stream_value(key: str) -> float | None:
    """Прочитать последнее значение из Redis Stream по ключу key.
    Ожидается формат записи стрима:
    {"metadata": {...}, "data": {"value": 18, ...}}
    """
    try:
        entries: list[tuple[bytes, dict[bytes, bytes]]] = cache.redis.xrevrange(  # type: ignore[assignment]
            key,
            max="+",
            min="-",
            count=1,
        )
    except ResponseError as e:
        logger.warning("Failed to read stream %s: %s", key, e)
        return None

    if not entries:
        return None

    _id, data = entries[0]
    if not data:
        return None

    # Берём поле "data" и ожидаем внутри JSON с объектом "data", в котором есть "value"
    raw_data: Any = data.get(b"data")
    if raw_data is None:
        return None

    try:
        s = raw_data.decode("utf-8") if isinstance(raw_data, (bytes, bytearray)) else str(raw_data)
        try:
            obj = json.loads(s)
        except (ValueError, TypeError):
            # иногда telemetry-service может писать dict repr (одинарные кавычки)
            obj = ast.literal_eval(s)
    except (ValueError, SyntaxError, TypeError):
        return None

    if not isinstance(obj, dict):
        return None

    inner = obj.get("data")
    if not isinstance(inner, dict):
        return None

    val = inner.get("value")
    if val is None:
        return None

    try:
        return float(val)
    except (TypeError, ValueError):
        return None

    return None


def get_vehicle_weight(vehicle_id: str | int) -> float | None:
    """Прочитать вес по vehicle_id из Redis Stream telemetry-service:weight:{vehicle_id}.
    Возвращает последнее значение weight/value или None, если данных нет.
    """
    key = redis_key(vehicle_id)
    return _read_last_stream_value(key)
