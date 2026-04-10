"""Модуль для обращения к api микросервиса: trip_service"""

import logging
from typing import Any

import httpx

from config.settings import get_settings

settings = get_settings()

ENTERPRISE_URL = settings.enterprise_service_url

logger = logging.getLogger(__name__)


class APIEnterpriseService:
    @staticmethod
    async def get_shift_info_by_timestamp(
        timestamp: str,  # Timestamp для определения смены (ISO format)
        work_regime_id: int | None = None,  # ID режима работы (если None - берется первый активный)
    ) -> dict[str, Any] | None:
        """Обёртка над enterprise-service /api/shift-service/get-shift-info-by-timestamp.

        Возвращает распарсенный JSON (с shift_date и shift_num или None если не найдено)
        """
        base_url = f"{ENTERPRISE_URL}/api/shift-service/get-shift-info-by-timestamp"

        params: dict[str, Any] = {
            "timestamp": timestamp,
        }
        if work_regime_id is not None:
            params["work_regime_id"] = work_regime_id

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(base_url, params=params)

            if resp.status_code == 200:
                return resp.json() or {}

            logger.debug(
                "enterprise-service /api/shift-service/get-shift-info-by-timestamp"
                " returned %s (url=%s, params=%s)",
                resp.status_code,
                base_url,
                params,
            )
            return None
        except Exception as e:
            logger.debug(
                "Failed to fetch get-shift-info-by-timestamp"
                " from enterprise-service: %s (url=%s, params=%s)",
                e,
                base_url,
                params,
            )
            raise

    @staticmethod
    async def get_vehicle(
        vehicle_id: int,
    ) -> dict[str, Any] | None:
        """Обёртка над enterprise-service /api/vehicles/{vehicle_id}.

        Возвращает распарсенный JSON (с vehicle или None если не найдено)
        """
        base_url = f"{ENTERPRISE_URL}/api/vehicles/{vehicle_id}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(base_url)

            if resp.status_code == 200:
                return resp.json() or {}

            logger.debug(
                "enterprise-service /api/vehicles/{vehicle_id} returned %s (url=%s, params=%s)",
                resp.status_code,
                base_url,
                "",
            )
            return None
        except Exception as e:
            logger.debug(
                "Failed to fetch vehicle from enterprise-service: %s (url=%s, params=%s)",
                e,
                base_url,
                "",
            )
            raise
