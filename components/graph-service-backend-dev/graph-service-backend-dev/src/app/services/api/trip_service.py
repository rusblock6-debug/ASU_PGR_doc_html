"""Модуль для обращения к api микросервиса: trip_service"""

import logging
from enum import StrEnum
from typing import Any

import httpx

from config.settings import get_settings

settings = get_settings()

TRIP_URL = settings.trip_service_url

logger = logging.getLogger(__name__)


# TODO Дублирование с trip_service/enums, тут либо типизация либо дублирование
class TripStatusRouteEnum(StrEnum):
    ACTIVE = "ACTIVE"  # В работе
    REJECTED = "REJECTED"  # Отклонено
    SENT = "SENT"  # Отправлено
    DELIVERED = "DELIVERED"  # Доставлено
    COMPLETED = "COMPLETED"  # Завершено
    EMPTY = "EMPTY"  # К заполнению
    PAUSED = "PAUSED"  # На паузе


class APITripService:
    @staticmethod
    async def get_list_shift_tasks(
        page: int = 1,
        size: int = 20,
        status_route_tasks: list[TripStatusRouteEnum] | None = None,
        shift_date: str | None = None,
        vehicle_ids: list[int] | None = None,
        shift_num: int | None = None,
    ) -> dict[str, Any] | None:
        """Обёртка над trip-service /api/shift-tasks.

        Возвращает распарсенный JSON (PaginatedResponse[ShiftTaskResponse])
        """
        base_url = f"{TRIP_URL}/api/shift-tasks"

        params: dict[str, Any] = {
            "page": page,
            "size": size,
        }
        if status_route_tasks is not None:
            params["status_route_tasks"] = [
                s.value if isinstance(s, TripStatusRouteEnum) else str(s)
                for s in status_route_tasks
            ]
        if shift_date is not None:
            params["shift_date"] = shift_date
        if vehicle_ids is not None:
            params["vehicle_ids"] = vehicle_ids
        if shift_num is not None:
            params["shift_num"] = shift_num

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(base_url, params=params)

            if resp.status_code == 200:
                return resp.json() or {}

            logger.debug(
                "trip-service /api/shift-tasks returned %s (url=%s, params=%s)",
                resp.status_code,
                base_url,
                params,
            )
            return None
        except Exception as e:
            logger.debug(
                "Failed to fetch shift_tasks from trip-service: %s (url=%s, params=%s)",
                e,
                base_url,
                params,
            )
            raise
