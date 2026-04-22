"""Утилиты для получения информации о местах из graph-service."""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.models import PlaceRemainingHistory


async def get_place(place_id: int) -> dict[str, Any] | None:
    """Получить информацию о месте по place_id из graph-service.

    Возвращает dict или None, если данных нет/не удалось распарсить.
    """
    try:
        place_info = await _get_place_info(place_id=place_id)
        if place_info is None:
            logger.warning(
                "Failed to get place_info",
                place_id=place_id,
                error="place_info is None",
            )
            return None

        return place_info
    except Exception as e:
        logger.warning(
            "Failed to fetch place from graph-service",
            place_id=place_id,
            error=str(e),
        )
        return None


async def _get_place_info(place_id: int) -> dict[str, Any] | None:
    url = f"{settings.graph_service_url}/api/places/{place_id}"

    try:
        async with httpx.AsyncClient(timeout=settings.enterprise_http_timeout_seconds) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning(
                    "Failed to fetch place info from graph-service",
                    place_id=place_id,
                    url=url,
                    status_code=resp.status_code,
                    response=(resp.text[:200] if resp.text else None),
                )
                return None

            try:
                payload = resp.json()
            except Exception as e:
                logger.warning(
                    "Failed to parse place info JSON response",
                    place_id=place_id,
                    url=url,
                    error=str(e),
                    response=(resp.text[:200] if resp.text else None),
                )
                return None

        if not isinstance(payload, dict):
            logger.warning(
                "Place info response is not a dict",
                place_id=place_id,
                url=url,
                payload_type=type(payload).__name__,
            )
            return None

        return payload
    except httpx.RequestError as e:
        logger.warning(
            "Request error while fetching place info",
            place_id=place_id,
            url=url,
            error=str(e),
        )
        return None
    except Exception as e:
        logger.warning(
            "Unexpected error while fetching place info",
            place_id=place_id,
            url=url,
            error=str(e),
        )
        return None


async def get_load_type(load_type_id: int) -> dict[str, Any] | None:
    """Получить информацию о виде груза по load_type_id из enterprise-service (bort).

    Возвращает dict или None, если данных нет/не удалось распарсить.
    """
    try:
        load_type_info = await _get_load_type_info(load_type_id=load_type_id)
        if load_type_info is None:
            logger.warning(
                "Failed to get load_type_info",
                load_type_id=load_type_id,
                error="load_type_info is None",
            )
            return None

        return load_type_info
    except Exception as e:
        logger.warning(
            "Failed to fetch load_type from enterprise-service",
            load_type_id=load_type_id,
            error=str(e),
        )
        return None


async def _get_load_type_info(load_type_id: int) -> dict[str, Any] | None:
    path = f"/api/load_types/{load_type_id}"

    url = f"{settings.enterprise_service_url}{path}"

    try:
        async with httpx.AsyncClient(timeout=settings.enterprise_http_timeout_seconds) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning(
                    "Failed to fetch load_type info from enterprise-service",
                    load_type_id=load_type_id,
                    url=url,
                    status_code=resp.status_code,
                    response=(resp.text[:200] if resp.text else None),
                )
                return None

            try:
                payload = resp.json()
            except Exception as e:
                logger.warning(
                    "Failed to parse load_type info JSON response",
                    load_type_id=load_type_id,
                    url=url,
                    error=str(e),
                    response=(resp.text[:200] if resp.text else None),
                )
                return None

        if not isinstance(payload, dict):
            logger.warning(
                "Load_type info response is not a dict",
                load_type_id=load_type_id,
                url=url,
                payload_type=type(payload).__name__,
            )
            return None

        return payload
    except httpx.RequestError as e:
        logger.warning(
            "Request error while fetching load_type info",
            load_type_id=load_type_id,
            url=url,
            error=str(e),
        )
        return None
    except Exception as e:
        logger.warning(
            "Unexpected error while fetching load_type info",
            load_type_id=load_type_id,
            url=url,
            error=str(e),
        )
        return None


async def get_place_stock(place_id: int, db: AsyncSession) -> float:
    """Получить актуальный остаток по месту, суммируя все change_volume из place_remaining_history.

    Args:
        place_id: ID места из graph-service
        db: Database session

    Returns:
        float: Сумма всех change_volume для данного place_id, или 0.0 если записей нет
    """
    try:
        query = select(func.sum(PlaceRemainingHistory.change_volume)).where(PlaceRemainingHistory.place_id == place_id)

        result = await db.execute(query)
        total = result.scalar()

        # Если записей нет, func.sum возвращает None, возвращаем 0.0
        return float(total) if total is not None else 0.0
    except Exception as e:
        logger.warning(
            "Failed to calculate place remaining",
            place_id=place_id,
            error=str(e),
        )
        return 0.0


async def recalculate_and_update_place_stock(
    place_id: int,
    db: AsyncSession,
) -> None:
    """Пересчитать остатки места и обновить их в graph-service.

    Args:
        place_id: ID места
        db: Сессия БД
    """
    try:
        current_stock = await get_place_stock(place_id=place_id, db=db)
        # Вызов graph-service API для обновления остатков
        graph_url = settings.graph_service_url
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.patch(
                f"{graph_url}/api/places/{place_id}",
                json={
                    "current_stock": current_stock,
                    "source": "system",
                },
            )
            if response.status_code == 200:
                logger.info("Updated stock in graph-service", place_id=place_id)
            else:
                logger.error(
                    "Failed to update stock in graph-service",
                    place_id=place_id,
                    status=response.status_code,
                    text=response.text,
                )
    except Exception as e:
        logger.error(
            "Error calling graph-service stock update",
            place_id=place_id,
            error=str(e),
        )
