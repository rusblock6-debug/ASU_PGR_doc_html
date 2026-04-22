"""Хеш graph-service:vehicle:{vehicle_id}:places — place_id, horizon."""

from __future__ import annotations

import logging
from typing import Any

from app.utils.redis import cache

from . import PLACES_SUFFIX, REDIS_KEY_PREFIX

logger = logging.getLogger(__name__)


def _places_key(vehicle_id: int) -> str:
    return f"{REDIS_KEY_PREFIX}{vehicle_id}{PLACES_SUFFIX}"


def save_vehicle_place(vehicle_id: str, place_id: int, horizon: int | None = None) -> None:
    """Сохранить place_id и горизонт в хеше graph-service:vehicle:{vehicle_id}:places."""
    key = _places_key(vehicle_id)  # type: ignore[arg-type]
    value: dict[str, Any] = {"place_id": place_id}
    if horizon is not None:
        value["horizon"] = horizon
    try:
        cache.dict_set(key, value)
        logger.debug(
            "Vehicle place saved: vehicle_id=%s place_id=%s horizon=%s",
            vehicle_id,
            place_id,
            horizon,
        )
    except Exception as e:
        logger.exception("Failed to save vehicle place to Redis: %s", e)


def get_vehicle_place(vehicle_id: int) -> dict[str, Any] | None:
    """Прочитать хеш graph-service:vehicle:{vehicle_id}:places (place_id, horizon)."""
    key = _places_key(vehicle_id)
    return cache.dict_get(key)


def get_all_vehicle_places() -> dict[str, dict[str, Any]]:
    """Все хеши graph-service:vehicle:*:places из Redis."""
    pattern = f"{REDIS_KEY_PREFIX}*{PLACES_SUFFIX}"
    keys = cache.redis.keys(pattern)
    result: dict[str, dict[str, Any]] = {}
    for k in keys:  # type: ignore[union-attr]
        key_str = k.decode("utf-8") if isinstance(k, bytes) else k
        data = cache.dict_get(key_str)
        if data and data.get("place_id") is not None:
            result[key_str] = data
    return result
