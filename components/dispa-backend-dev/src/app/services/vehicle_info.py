"""Утилиты для получения информации о машине.

Сейчас используется для получения нормативной грузоподъёмности, чтобы:
- вычислять `place_remaining_change.change_volume` (через вес и плотность)

Источник данных: enterprise-service (в бортовом окружении).
"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from app.core.config import settings


async def get_load_capacity(vehicle_id: int) -> float | None:
    r"""Получить нормативный объем кузова\ковша из enterprise-service (bort).

    Возвращает float или None, если данных нет/не удалось распарсить.

    """
    try:
        vehicle_info = await _get_vehicle_info(vehicle_id=vehicle_id)
        if vehicle_info is None:
            logger.warning(
                "Failed to get vehicle_info",
                vehicle_id=vehicle_id,
                error="vehicle_info is None",
            )
            return None

        model_id = vehicle_info.get("model_id")

        if model_id is None:
            logger.warning(
                "Failed to get model_id from vehicle",
                vehicle_id=vehicle_id,
                error="None model_id in vehicle_info",
            )
            return None

        model_info = await _get_model_info(model_id=model_id)
        if model_info is None:
            logger.warning(
                "Failed to get model_info",
                vehicle_id=vehicle_id,
                model_id=model_id,
                error="model_info is None",
            )
            return None

        load_capacity = model_info.get("load_capacity_tons")

        if load_capacity is None:
            logger.warning(
                "Failed to get load_capacity from model",
                vehicle_id=vehicle_id,
                error="None load_capacity in model_info",
            )
            return None

        return load_capacity
    except Exception as e:
        logger.warning(
            "Failed to fetch load capacity from enterprise-service",
            vehicle_id=vehicle_id,
            error=str(e),
        )
        return None


async def _get_vehicle_info(vehicle_id: int) -> dict[str, Any] | None:
    path = settings.enterprise_vehicle_info_path.format(vehicle_id=vehicle_id)

    if not path.startswith("/"):
        path = "/" + path

    url = f"{settings.enterprise_service_url}{path}"

    try:
        async with httpx.AsyncClient(timeout=settings.enterprise_http_timeout_seconds) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning(
                    "Failed to fetch vehicle info from enterprise-service",
                    vehicle_id=vehicle_id,
                    url=url,
                    status_code=resp.status_code,
                    response=(resp.text[:200] if resp.text else None),
                )
                return None

            try:
                payload = resp.json()
            except Exception as e:
                logger.warning(
                    "Failed to parse vehicle info JSON response",
                    vehicle_id=vehicle_id,
                    url=url,
                    error=str(e),
                    response=(resp.text[:200] if resp.text else None),
                )
                return None

        if not isinstance(payload, dict):
            logger.warning(
                "Vehicle info response is not a dict",
                vehicle_id=vehicle_id,
                url=url,
                payload_type=type(payload).__name__,
            )
            return None

        return payload
    except httpx.RequestError as e:
        logger.warning(
            "Request error while fetching vehicle info",
            vehicle_id=vehicle_id,
            url=url,
            error=str(e),
        )
        return None
    except Exception as e:
        logger.warning(
            "Unexpected error while fetching vehicle info",
            vehicle_id=vehicle_id,
            url=url,
            error=str(e),
        )
        return None


async def _get_model_info(model_id: int) -> dict[str, Any] | None:
    path = settings.enterprise_model_info_path.format(model_id=model_id)

    if not path.startswith("/"):
        path = "/" + path

    url = f"{settings.enterprise_service_url}{path}"

    try:
        async with httpx.AsyncClient(timeout=settings.enterprise_http_timeout_seconds) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning(
                    "Failed to fetch model info from enterprise-service",
                    model_id=model_id,
                    url=url,
                    status_code=resp.status_code,
                    response=(resp.text[:200] if resp.text else None),
                )
                return None

            try:
                payload = resp.json()
            except Exception as e:
                logger.warning(
                    "Failed to parse model info JSON response",
                    model_id=model_id,
                    url=url,
                    error=str(e),
                    response=(resp.text[:200] if resp.text else None),
                )
                return None

        if not isinstance(payload, dict):
            logger.warning(
                "Model info response is not a dict",
                model_id=model_id,
                url=url,
                payload_type=type(payload).__name__,
            )
            return None

        return payload
    except httpx.RequestError as e:
        logger.warning(
            "Request error while fetching model info",
            model_id=model_id,
            url=url,
            error=str(e),
        )
        return None
    except Exception as e:
        logger.warning(
            "Unexpected error while fetching model info",
            model_id=model_id,
            url=url,
            error=str(e),
        )
        return None
