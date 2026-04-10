"""Сервис для работы с поиском ближайших меток (locations)"""

import json
from datetime import timedelta

# import logging
from typing import TYPE_CHECKING

import httpx
import pygeohash as geohash
from fastapi import HTTPException
from geoalchemy2.functions import ST_X, ST_Y
from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.logging import setup_logger
from app.models.database import Place, Tag
from app.schemas.locations import LocationResponse
from app.services.crud import TagsCRUD
from app.utils.redis import cache
from config.database import AsyncSessionLocal
from config.settings import get_settings

settings = get_settings()

if TYPE_CHECKING:
    pass


# logger = logging.getLogger(__name__)
setup_logger()


class LocationFinder:
    def __init__(self, precision: int = 12) -> None:
        """precision: точность геохэша (1-12)
        Чем выше precision, тем меньше зона
        """
        self.precision = precision

    async def add_db_tags(self, id: int | None = None) -> None:
        async with AsyncSessionLocal() as session:
            if id is None:
                # данный функционал нужен только при его введении,
                # чтобы обработать уже существующие теги
                tags = await TagsCRUD(session).get_with_relation_for_geo()
                for db_tag in tags:
                    result = await self._check_location(db_tag, session)
                    if result is None:
                        continue
                    lat, lon, tag = result
                    self.add_location(
                        lat,
                        lon,
                        tag.place_id,
                        tag.place.horizon.height if tag.place.horizon else 0.0,
                        tag.id,
                        tag.radius,
                        tag.tag_name,
                        tag.place.name,
                        tag.place.type,
                    )
            else:
                db_tag = await TagsCRUD(session).get_by_id(id)
                if db_tag is None:
                    logger.warning("Tag not found", tag_id=id)
                    return
                result = await self._check_location(db_tag, session)
                if result is None:
                    logger.warning(
                        "Tag has no valid location (no place or non-GPS coordinates)",
                        tag_id=id,
                    )
                    return
                lat, lon, tag = result
                self.add_location(
                    lat,
                    lon,
                    tag.place_id,
                    tag.place.horizon.height if tag.place.horizon else 0.0,
                    tag.id,
                    tag.radius,
                    tag.tag_name,
                    tag.place.name,
                    tag.place.type,
                )

    async def update_db_tag(
        self,
        id: int,
    ):
        async with AsyncSessionLocal() as session:
            db_tag = await TagsCRUD(session).get_by_id(id)
            if db_tag is None:
                logger.warning("Tag not found", tag_id=id)
                return
            result = await self._check_location(db_tag, session)
            if result is None:
                logger.warning(
                    "Tag has no valid location (no place or non-GPS coordinates)",
                    tag_id=id,
                )
                return
            lat, lon, tag = result
            gh = self._hash_location(lat, lon)
            geo_in_state = cache.dict_get(f"geo:{gh}")
            if geo_in_state is not None:
                cache.dict_set(
                    f"geo:{gh}",
                    {
                        "lat": lat,
                        "lon": lon,
                        "place_id": tag.place_id,
                        "horizon": tag.place.horizon.height
                        if tag.place and tag.place.horizon
                        else 0.0,
                        "tag_id": tag.id,
                        "tag_radius": tag.radius,
                        "tag_name": tag.tag_name,
                        "place_name": tag.place.name if tag.place else "",
                        "place_type": tag.place.type if tag.place else "",
                    },
                )
                logger.info("Location was updated", tag_id=tag.id, place_id=tag.place_id)
            else:
                logger.info("Location not found", tag_id=tag.id, place_id=tag.place_id)

    async def remove_db_tag(
        self,
        id: int,
    ):
        async with AsyncSessionLocal() as session:
            db_tag = await TagsCRUD(session).get_by_id(id)
            if db_tag is None:
                logger.warning("Tag not found", tag_id=id)
                return
            result = await self._check_location(db_tag, session)
            if result is None:
                logger.warning(
                    "Tag has no valid location (no place or non-GPS coordinates)",
                    tag_id=id,
                )
                return
            lat, lon, _ = result
            gh = self._hash_location(lat, lon)
            geo_in_state = cache.dict_get(f"geo:{gh}")
            if geo_in_state is not None:
                cache.delete(f"geo:{gh}")
                logger.info("Location was deleted")
            else:
                logger.info("Location not found", geohash=gh)

    async def remove_db_tags(
        self,
    ):
        """Удаляет из кэша все ключи вида geo:* (все геолокации тегов)."""
        cache.clean_by_key("geo:")
        logger.info("All redis location cache was deleted")

    async def _check_location(self, tag: Tag, session: AsyncSession) -> tuple | None:
        """Проверяет и добавляет локацию тега, извлекая координаты из geometry"""
        if not tag.place or not tag.place_id:
            return None

        # Извлекаем координаты из geometry через SQL запрос
        result = await session.execute(
            select(
                ST_X(Place.geometry).label("lon"),
                ST_Y(Place.geometry).label("lat"),
            ).where(Place.id == tag.place_id),
        )
        row = result.first()

        if row and row.lat is not None and row.lon is not None:
            lat = float(row.lat)
            lon = float(row.lon)

            # Проверяем, что координаты являются валидными GPS координатами
            # GPS широта должна быть между -90 и 90, долгота между -180 и 180
            # Если координаты вне этого диапазона, это Canvas координаты, пропускаем их
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                logger.warning(
                    f"Skipping tag {tag.id} (place {tag.place_id}): "
                    f"coordinates ({lat}, {lon}) are not valid GPS coordinates. "
                    f"These appear to be Canvas coordinates, not GPS.",
                )
                return None

            return lat, lon, tag

        return None

    def add_location(
        self,
        lat: float,
        lon: float,
        place_id: int,
        horizon: float,
        tag_id: int,
        tag_radius: float,
        tag_name: str,
        place_name: str,
        place_type: str,
    ) -> None:
        """Добавляет локацию в индекс"""
        gh = self._hash_location(lat, lon)
        geo_in_state = cache.dict_get(f"geo:{gh}")
        if not geo_in_state:
            cache.dict_set(
                f"geo:{gh}",
                {
                    "lat": lat,
                    "lon": lon,
                    "place_id": place_id,
                    "horizon": horizon,
                    "tag_id": tag_id,
                    "tag_radius": tag_radius,
                    "tag_name": tag_name,
                    "place_name": place_name,
                    "place_type": place_type,
                },
            )
            logger.info("Added location ", tag_id=tag_id, place_id=place_id)
            return
        logger.info("Location was added before", tag_id=tag_id, place_id=place_id)

    def _hash_location(self, lat: float, lon: float) -> str:
        return geohash.encode(lat, lon, precision=self.precision)

    def find_nearest(self, lat: float, lon: float):
        """Находит ближайшие локации в радиусе действия метки (тега)"""
        all_geo_in_state = cache.dict_get_all("geo")
        gh = self._hash_location(lat, lon)

        for hash, data in all_geo_in_state.items():
            distance = geohash.geohash_haversine_distance(gh, hash.split(":")[-1])
            radius = data.get("tag_radius")
            if radius is not None and distance <= radius:
                return LocationResponse(
                    tag_id=data.get("tag_id"),
                    tag_name=data.get("tag_name"),
                    place_id=data.get("place_id"),
                    place_name=data.get("place_name"),
                    place_type=data.get("place_type"),
                )
        logger.info(f"No tag found within radius at GPS coords: lat={lat}, lon={lon}")
        return LocationResponse(
            tag_id=None,
            tag_name=None,
            place_id=None,
            place_name=None,
            place_type=None,
        )

    async def calculate_route(
        self,
        start_node_id: int,
        target_node_id: int,
        db: AsyncSession,
        use_cache: bool = True,
    ) -> dict:
        # Валидация входных данных
        if start_node_id <= 0 or target_node_id <= 0:
            raise ValueError("start_node_id и target_node_id должны быть положительными числами.")
        if start_node_id == target_node_id:
            raise ValueError("start_node_id и target_node_id не должны совпадать.")

        cache_key = f"route:{start_node_id}:{target_node_id}"

        # Попытка получить из кеша
        if use_cache:
            try:
                cached = cache.dict_get(cache_key)
                if cached:
                    # Десериализуем поля
                    route_geojson = json.loads(cached["route_geojson"])
                    total_length = float(cached["total_length_m"])
                    edge_ids = json.loads(cached["edge_ids"]) if cached["edge_ids"] else []
                    # Проверяем соответствие узлов (на случай коллизий)
                    if (
                        int(cached["start_node_id"]) == start_node_id
                        and int(
                            cached["target_node_id"],
                        )
                        == target_node_id
                    ):
                        logger.debug(f"Маршрут {cache_key} получен из кеша")
                        return {
                            "route_geojson": route_geojson,
                            "total_length_m": round(total_length, 2),
                            "edge_ids": edge_ids,
                            "start_node_id": start_node_id,
                            "target_node_id": target_node_id,
                        }
                    else:
                        # Несоответствие данных – удаляем ключ
                        cache.delete(cache_key)
                        logger.warning(f"Несоответствие узлов в кеше для {cache_key}, удаляем.")
            except Exception as e:
                logger.warning(f"Ошибка чтения кеша для {cache_key}: {e}. Удаляем ключ.")
                cache.delete(cache_key)

        # SQL с pgr_dijkstra
        route_sql = text(  # noqa: S608
            """
            WITH route AS (
                SELECT *
                FROM pgr_dijkstra(
                    'SELECT id,
                            from_node_id AS source,
                            to_node_id   AS target,
                            ST_Length(geometry::geography) AS cost
                    FROM graph_edges',
                    CAST(:start_id AS bigint),
                    CAST(:target_id AS bigint),
                    false
                )
            )
            SELECT
                ST_AsGeoJSON(ST_MakeLine(gn.geometry ORDER BY route.seq)) AS geom_geojson,
                ST_Length(ST_MakeLine(gn.geometry)::geography)           AS total_length,
                array_agg(route.edge ORDER BY route.seq)                 AS edge_ids
            FROM route
            JOIN graph_edges ge ON route.edge = ge.id
            JOIN graph_nodes gn ON route.node = gn.id
            GROUP BY route.start_vid, route.end_vid;
            """,
        )

        try:
            result = await db.execute(
                route_sql,
                {"start_id": start_node_id, "target_id": target_node_id},
            )
            row = result.fetchone()

            if not row or not row.geom_geojson:
                raise ValueError(
                    f"Маршрут между узлами {start_node_id} и {target_node_id} не найден.",
                )

            route_geojson = json.loads(row.geom_geojson)
            total_length = float(row.total_length)
            edge_ids = row.edge_ids if row.edge_ids else []

            response_data = {
                "route_geojson": route_geojson,
                "total_length_m": round(total_length, 2),
                "edge_ids": edge_ids,
                "start_node_id": start_node_id,
                "target_node_id": target_node_id,
            }

            # Сохраняем в кеш
            if use_cache:
                try:
                    cache_data = {
                        "route_geojson": json.dumps(route_geojson, ensure_ascii=False),
                        "total_length_m": str(round(total_length, 2)),
                        "edge_ids": json.dumps(edge_ids),
                        "start_node_id": str(start_node_id),
                        "target_node_id": str(target_node_id),
                    }
                    cache.dict_set(cache_key, cache_data)
                    cache.redis.expire(cache_key, settings.route_cache_ttl)
                    logger.debug(f"Маршрут {cache_key} сохранен в кеш")
                except Exception as e:
                    logger.error(f"Не удалось сохранить маршрут в кеш: {e}")

            return response_data

        except Exception as e:
            logger.error(f"Ошибка вычисления маршрута: {e}")
            raise

    async def calculate_route_progress(
        self,
        route_data: dict,
        lat: float,
        lon: float,
        db: AsyncSession,
    ) -> dict:
        """Вычисляет прогресс вдоль маршрута на основе текущего положения,
        используя PostGIS для точных географических вычислений.

        Параметры:
            route_data: словарь от calculate_route (route_geojson, total_length_m)
            lat: широта текущего положения
            lon: долгота текущего положения
            db: сессия БД

        Возвращает словарь с ключами:
            - user_location: {"lat": lat, "lon": lon}
            - nearest_point_on_route: {"lat": ..., "lon": ...} или None
            - distance_covered_m: float
            - distance_remaining_m: float
            - percent_complete: float
            - distance_to_route: float (расстояние от точки до линии, метры)
        """
        progress_sql = text(  # noqa: S608
            """
            WITH route_line AS (
                SELECT ST_SetSRID(
                    ST_GeomFromGeoJSON(:route_geojson), 4326
                ) AS geom
            )
            SELECT
                ST_Distance(
                    geom::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                ) AS distance_to_route,
                ST_LineLocatePoint(
                    geom,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                ) AS fraction,
                ST_AsGeoJSON(ST_LineInterpolatePoint(
                    geom,
                    ST_LineLocatePoint(
                        geom,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                    )
                )) AS nearest_point_geojson
            FROM route_line
            """,
        ).bindparams(lon=lon, lat=lat)

        try:
            result = await db.execute(
                progress_sql,
                {"route_geojson": json.dumps(route_data["route_geojson"])},
            )
            row = result.fetchone()
            if not row:
                raise ValueError("Не удалось вычислить прогресс")
        except Exception as e:
            logger.error(f"Ошибка запроса прогресса: {e}")
            raise

        distance_to_route = float(row.distance_to_route)
        fraction = float(row.fraction) if row.fraction is not None else 0.0
        nearest_point_geojson = (
            json.loads(row.nearest_point_geojson) if row.nearest_point_geojson else None
        )

        total_length = route_data["total_length_m"]
        covered = fraction * total_length
        remaining = total_length - covered
        percent = (covered / total_length) * 100 if total_length > 0 else 0

        nearest_point = None
        if nearest_point_geojson:
            nearest_lon, nearest_lat, _ = nearest_point_geojson["coordinates"]
            nearest_point = {"lat": nearest_lat, "lon": nearest_lon}

        return {
            "user_location": {"lat": lat, "lon": lon},
            "nearest_point_on_route": nearest_point,
            "distance_covered_m": round(covered, 2),
            "distance_remaining_m": round(remaining, 2),
            "percent_complete": round(percent, 1),
            "distance_to_route": round(distance_to_route, 2),
        }

    async def find_nearest_node_to_bort(self, lat: float, lon: float, db: AsyncSession) -> int:
        """Возвращает ID узла графа, ближайшего к заданным координатам.
        Использует оператор <-> для эффективного поиска (требуется GiST индекс).
        """
        query = text("""
            SELECT id
            FROM graph_nodes
            ORDER BY geometry <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
            LIMIT 1
        """)
        result = await db.execute(query, {"lon": lon, "lat": lat})
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Не найден ближайший узел")
        return row[0]

    async def calculate_time_to_destination(self, distance_m: int | None):
        raw_vehicle_id = settings.vehicle_id
        try:
            vehicle_id = int(raw_vehicle_id)
        except Exception as _:
            return None

        url = (
            f"http://{settings.enterprise_service_host}:"
            f"{settings.enterprise_service_internal_port}/api/vehicles/{vehicle_id}/speed"
        )
        headers = {"accept": "application/json"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=5.0)
                response.raise_for_status()
                data = response.json()
                speed_kmh = data.get("speed")
                if speed_kmh is None:
                    logger.error("Ответ не содержит поле 'speed'")
                    return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка при запросе скорости: {e}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Ошибка соединения при запросе скорости: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при запросе скорости: {e}")
            return None

        if speed_kmh <= 0:
            logger.warning(f"Скорость должна быть положительной, получено: {speed_kmh}")
            return None

        logger.info(f"speed_kmh: {speed_kmh}")

        speed_ms = speed_kmh * 1000 / 3600  # км/ч в м/с
        time_seconds = distance_m / speed_ms

        # Форматирование
        td = timedelta(seconds=time_seconds)
        hours = td.seconds // 3600
        minutes = (td.seconds % 3600) // 60
        seconds = td.seconds % 60

        return {
            "total_seconds": round(time_seconds, 1),
            "formatted": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds,
        }


loc_finder = LocationFinder()
