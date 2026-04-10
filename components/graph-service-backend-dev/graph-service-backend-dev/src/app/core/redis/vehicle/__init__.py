"""Базовый модуль Redis для транспортных средств.
Содержит общий префикс ключей и вспомогательную функцию формирования ключа.
"""

from __future__ import annotations

REDIS_KEY_PREFIX = "graph-service:vehicle:"
PLACES_SUFFIX = ":places"
STATE_SUFFIX = ":state"


def redis_key(vehicle_id: str | int) -> str:
    """Базовый префикс ключа для ТС (без :places/:state)."""
    return f"{REDIS_KEY_PREFIX}{vehicle_id}"
