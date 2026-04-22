"""Хеш graph-service:vehicle:{vehicle_id}:state — поле state."""

from __future__ import annotations

import logging

from app.utils.redis import cache

from . import REDIS_KEY_PREFIX, STATE_SUFFIX

logger = logging.getLogger(__name__)


def _state_key(vehicle_id: int) -> str:
    return f"{REDIS_KEY_PREFIX}{vehicle_id}{STATE_SUFFIX}"


def save_vehicle_state(vehicle_id: int, state: str) -> None:
    """Сохранить state в хеше graph-service:vehicle:{vehicle_id}:state."""
    key = _state_key(vehicle_id)
    try:
        cache.dict_set(key, {"state": state})
        logger.debug("Vehicle state saved: vehicle_id=%s state=%s", vehicle_id, state)
    except Exception as e:
        logger.exception("Failed to save vehicle state to Redis: %s", e)


def get_vehicle_state(vehicle_id: int) -> str | None:
    """Прочитать state из хеша graph-service:vehicle:{vehicle_id}:state."""
    key = _state_key(vehicle_id)
    data = cache.dict_get(key)
    if not data:
        return None
    val = data.get("state")
    return str(val) if val is not None else None


def get_all_vehicle_states() -> dict[str, str]:
    """Все ключи graph-service:vehicle:*:state и значение поля state."""
    pattern = f"{REDIS_KEY_PREFIX}*{STATE_SUFFIX}"
    keys = cache.redis.keys(pattern)
    result: dict[str, str] = {}
    for k in keys:  # type: ignore[union-attr]
        key_str = k.decode("utf-8") if isinstance(k, bytes) else k
        data = cache.dict_get(key_str)
        if data and data.get("state") is not None:
            result[key_str] = str(data["state"])
    return result
