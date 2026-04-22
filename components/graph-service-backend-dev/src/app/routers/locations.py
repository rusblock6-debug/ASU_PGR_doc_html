"""API для поиска ближайшей метки по GPS координатам"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.locations import (
    LocationRequest,
    LocationResponse,
    RouteNodesResponse,
    RouteProgressResponse,
)
from app.services.locations import loc_finder
from app.services.place_route_nodes import get_primary_node_id_per_place
from config.database import get_async_db
from config.settings import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

location_router = APIRouter(prefix="/location", tags=["Locations"])
route_router = APIRouter(prefix="/route", tags=["Routes"])


@location_router.post("/find", response_model=LocationResponse)
async def find_nearest_tag(
    location_data: LocationRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """Найти ближайшую метку по GPS координатам
    1) eKuiper отправляет GPS координаты {lat, lon} на /api/location/find
    2) Endpoint конвертирует GPS → Canvas координаты
    3) Ищет метку в радиусе которой находится точка
    4) Возвращает {point_id, point_name, point_type}
    5) eKuiper публикует результат в MQTT truck/{id}/sensor/tag/events
    6) Graph Backend получает tag через MQTT и передаёт на фронтенд через WebSocket
    """
    try:
        return loc_finder.find_nearest(location_data.lat, location_data.lon)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.errors()) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@route_router.get("/place-node-ids")
async def resolve_place_graph_node_ids(
    place_ids: list[int] = Query(..., description="ID мест (ПП/ПР) для привязки к узлам графа"),
    db: AsyncSession = Depends(get_async_db),
):
    """Возвращает первый graph node_id для каждого place_id.

    Используется та же логика, что у live route stream.
    """
    unique = {int(p) for p in place_ids if p is not None}
    mapping = await get_primary_node_id_per_place(db, unique)
    return {"nodes": {str(pid): nid for pid, nid in sorted(mapping.items())}}


@route_router.get("/{start_node_id}/{target_node_id}", response_model=RouteNodesResponse)
async def get_route_to_nodes(
    start_node_id: int,
    target_node_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await loc_finder.calculate_route(start_node_id, target_node_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка сервера при расчете маршрута: {str(e)}",
        ) from e


@route_router.get(
    "/progress/{start_node_id}/{target_node_id}",
    response_model=RouteProgressResponse,
)
async def get_route_progress(
    start_node_id: int,
    target_node_id: int,
    lat: float,
    lon: float,
    db: AsyncSession = Depends(get_async_db),
):
    # Получаем исходный маршрут
    try:
        route_data = await loc_finder.calculate_route(start_node_id, target_node_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения маршрута: {str(e)}") from e

    # Вычисляем прогресс
    # try:
    progress = await loc_finder.calculate_route_progress(route_data, lat, lon, db)
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=f"Ошибка вычисления прогресса: {str(e)}")

    # Проверка отклонения
    if progress["distance_to_route"] > settings.deviation_threshold_m:
        # Поиск ближайшего узла
        try:
            nearest_node_id = await loc_finder.find_nearest_node_to_bort(lat, lon, db)
        except HTTPException:
            # Если узел не найден, просто отмечаем отклонение, но маршрут не меняем
            logger.warning("Не удалось найти ближайший узел при отклонении")
            # Добавляем флаг отклонения в ответ

            # calculate_time
            time_data = await loc_finder.calculate_time_to_destination(
                progress.get("distance_remaining_m"),
            )

            return {
                "start_node_id": start_node_id,
                "target_node_id": target_node_id,
                **progress,
                "deviation_detected": True,
                "new_route": False,
                "route_geojson": route_data["route_geojson"],
                "total_length_m": route_data["total_length_m"],
                "edge_ids": route_data["edge_ids"],
                "time_data": time_data,
            }

        if nearest_node_id != start_node_id:
            # Строим новый маршрут
            new_route = await loc_finder.calculate_route(nearest_node_id, target_node_id, db)
            # Для нового маршрута прогресс обнулён (кроме user_location)

            # calculate_time
            time_data = await loc_finder.calculate_time_to_destination(
                new_route.get("total_length_m"),
            )

            return {
                "start_node_id": nearest_node_id,
                "target_node_id": target_node_id,
                "user_location": {"lat": lat, "lon": lon},
                "nearest_point_on_route": None,
                "distance_covered_m": 0,
                "distance_remaining_m": new_route["total_length_m"],
                "percent_complete": 0,
                "deviation_detected": True,
                "new_route": True,
                "route_geojson": new_route["route_geojson"],
                "total_length_m": new_route["total_length_m"],
                "edge_ids": new_route["edge_ids"],
                "time_data": time_data,
            }

    # calculate_time
    time_data = await loc_finder.calculate_time_to_destination(progress.get("distance_remaining_m"))

    # Если отклонения нет или не удалось перестроить – возвращаем исходный прогресс
    return {
        "start_node_id": start_node_id,
        "target_node_id": target_node_id,
        **progress,
        "deviation_detected": False,
        "new_route": False,
        "route_geojson": route_data["route_geojson"],
        "total_length_m": route_data["total_length_m"],
        "edge_ids": route_data["edge_ids"],
        "time_data": time_data,
    }
