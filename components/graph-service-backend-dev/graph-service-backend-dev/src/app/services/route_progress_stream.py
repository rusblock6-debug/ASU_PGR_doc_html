"""SSE helpers for live vehicle placement on route cards."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis.vehicle.vehicle_state import get_vehicle_state
from app.models.database import VehicleLocation
from app.services.api.enterprise_service import APIEnterpriseService
from app.services.api.trip_service import APITripService, TripStatusRouteEnum
from app.services.live_vehicle_locations import get_for_vehicle_ids as get_live_locations
from app.services.locations import loc_finder
from app.services.place_route_nodes import get_primary_node_id_per_place
from config.database import AsyncSessionLocal
from config.settings import get_settings

RouteCacheEntry = tuple[datetime, dict[str, Any]]

_route_cache: dict[tuple[int, int], RouteCacheEntry] = {}
settings = get_settings()

# Направление движения вдоль геометрии ПП→ПР:
# сравнение progress между секундами (без доп. запросов).
_vehicle_last_route_percent: dict[int, float] = {}
_vehicle_last_is_forward: dict[int, bool] = {}
_PROGRESS_DELTA_EPSILON_PCT = 0.25
_SHIFT_INFO_CACHE_TTL_SECONDS = 300.0
_shift_info_cache: tuple[dict[str, Any], float] | None = None
_ACTIVE_ROUTES_CACHE_TTL_SECONDS = 5.0
_active_routes_cache: tuple[list[tuple[int, int, int]], float] | None = None


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _clamp_progress(value: float | int | None) -> float:
    if value is None:
        return 50.0
    return max(0.0, min(100.0, float(value)))


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


async def _get_current_shift_info_cached() -> dict[str, Any] | None:
    global _shift_info_cache

    if _shift_info_cache is not None:
        cached_shift_info, cached_at = _shift_info_cache
        if time.monotonic() - cached_at < _SHIFT_INFO_CACHE_TTL_SECONDS:
            return cached_shift_info

    shift_info = await APIEnterpriseService.get_shift_info_by_timestamp(
        timestamp=_now_utc().isoformat(),
    )
    if not isinstance(shift_info, dict):
        return None

    _shift_info_cache = (shift_info, time.monotonic())
    return shift_info


async def _fetch_active_vehicle_routes() -> list[tuple[int, int, int]]:
    """Получить активные (ACTIVE) маршруты в виде (vehicle_id, place_a_id, place_b_id)."""
    global _active_routes_cache

    if _active_routes_cache is not None:
        cached_routes, cached_at = _active_routes_cache
        if time.monotonic() - cached_at < _ACTIVE_ROUTES_CACHE_TTL_SECONDS:
            return cached_routes

    shift_info = await _get_current_shift_info_cached()
    if not isinstance(shift_info, dict):
        return []

    shift_date = shift_info.get("shift_date")
    shift_num_raw = shift_info.get("shift_num")
    if not isinstance(shift_date, str) or not shift_date:
        return []
    if shift_num_raw is None:
        return []
    if isinstance(shift_num_raw, int):
        shift_num = shift_num_raw
    else:
        try:
            shift_num = int(str(shift_num_raw))
        except (TypeError, ValueError):
            return []

    page = 1
    size = 100
    latest_active_route_by_vehicle: dict[int, tuple[datetime, tuple[int, int, int]]] = {}

    while True:
        payload = await APITripService.get_list_shift_tasks(
            page=page,
            size=size,
            status_route_tasks=[TripStatusRouteEnum.ACTIVE],
            shift_date=shift_date,
            shift_num=shift_num,
        )
        if not isinstance(payload, dict):
            break

        items = payload.get("items")
        if not isinstance(items, list) or not items:
            break

        for shift_task in items:
            if not isinstance(shift_task, dict):
                continue
            vehicle_raw = shift_task.get("vehicle_id")
            if vehicle_raw is None:
                continue
            try:
                vehicle_id = int(vehicle_raw)
            except (TypeError, ValueError):
                continue

            route_tasks = shift_task.get("route_tasks")
            if not isinstance(route_tasks, list):
                continue

            for route_task in route_tasks:
                if not isinstance(route_task, dict):
                    continue
                if str(route_task.get("status", "")).lower() != "active":
                    continue
                place_a_raw = route_task.get("place_a_id")
                place_b_raw = route_task.get("place_b_id")
                if place_a_raw is None or place_b_raw is None:
                    continue
                try:
                    place_a_id = int(place_a_raw)
                    place_b_id = int(place_b_raw)
                except (TypeError, ValueError):
                    continue

                route_ts = (
                    _parse_iso_datetime(route_task.get("updated_at"))
                    or _parse_iso_datetime(route_task.get("created_at"))
                    or _parse_iso_datetime(shift_task.get("updated_at"))
                    or _parse_iso_datetime(shift_task.get("created_at"))
                    or datetime.min.replace(tzinfo=UTC)
                )
                current = latest_active_route_by_vehicle.get(vehicle_id)
                if current is None or route_ts >= current[0]:
                    latest_active_route_by_vehicle[vehicle_id] = (
                        route_ts,
                        (vehicle_id, place_a_id, place_b_id),
                    )

        total = payload.get("total")
        if not isinstance(total, int):
            break
        if page * size >= total:
            break
        page += 1

    result = [v[1] for v in latest_active_route_by_vehicle.values()]
    _active_routes_cache = (result, time.monotonic())
    return result


def _normalize_vehicle_id_for_db(raw: str) -> int | None:
    """Map DB vehicle_id string to int: '4' -> 4, '4_truck' -> 4."""
    try:
        return int(raw.split("_")[0])
    except (ValueError, AttributeError):
        return None


async def _get_latest_vehicle_locations(
    db: AsyncSession,
    vehicle_ids: set[int],
) -> dict[int, dict[str, float]]:
    if not vehicle_ids:
        return {}

    # Живой кэш из MQTT (тот же источник, что и WebSocket vehicle-tracking)
    locations: dict[int, dict[str, float]] = get_live_locations(vehicle_ids)

    # БД: ищем по "4" и "4_truck", чтобы не зависеть от формата в топике
    vehicle_id_strings = list({s for v in vehicle_ids for s in (str(v), f"{v}_truck")})
    latest_locations_subquery = (
        select(
            VehicleLocation.vehicle_id.label("vehicle_id"),
            func.max(VehicleLocation.timestamp).label("max_timestamp"),
        )
        .where(VehicleLocation.vehicle_id.in_(vehicle_id_strings))
        .group_by(VehicleLocation.vehicle_id)
        .subquery()
    )

    query = select(
        VehicleLocation.vehicle_id,
        func.ST_Y(VehicleLocation.geometry).label("lat"),
        func.ST_X(VehicleLocation.geometry).label("lon"),
    ).join(
        latest_locations_subquery,
        and_(
            VehicleLocation.vehicle_id == latest_locations_subquery.c.vehicle_id,
            VehicleLocation.timestamp == latest_locations_subquery.c.max_timestamp,
        ),
    )

    rows = (await db.execute(query)).all()
    for vehicle_id_raw, lat, lon in rows:
        vid = _normalize_vehicle_id_for_db(str(vehicle_id_raw))
        if vid is None or vid not in vehicle_ids or (lat is None or lon is None):
            continue
        # Живой кэш приоритетнее; если в кэше нет — берём из БД
        if vid not in locations:
            locations[vid] = {"lat": float(lat), "lon": float(lon)}

    return locations


async def _get_route_data(
    start_node_id: int,
    target_node_id: int,
    db: AsyncSession,
) -> dict[str, Any] | None:
    cache_key = (start_node_id, target_node_id)
    cached = _route_cache.get(cache_key)
    now = _now_utc()

    if cached is not None:
        cached_at, route_data = cached
        if (now - cached_at).total_seconds() < settings.route_cache_ttl:
            return route_data

    try:
        route_data = await loc_finder.calculate_route(start_node_id, target_node_id, db)
    except Exception as exc:
        logger.warning(
            "Failed to calculate route for live route stream",
            start_node_id=start_node_id,
            target_node_id=target_node_id,
            error=str(exc),
        )
        return None

    _route_cache[cache_key] = (now, route_data)
    return route_data


async def build_route_progress_updates() -> list[dict[str, Any]]:
    try:
        active_vehicle_routes = await _fetch_active_vehicle_routes()
    except Exception as exc:
        logger.warning("Failed to fetch in-progress routes for route stream", error=str(exc))
        return []

    if not active_vehicle_routes:
        return []

    place_ids = {
        place_id
        for _, place_a_id, place_b_id in active_vehicle_routes
        for place_id in (place_a_id, place_b_id)
    }
    vehicle_ids = {vehicle_id for vehicle_id, _, _ in active_vehicle_routes}
    timestamp = _now_utc().isoformat()

    active_vehicle_ids = {vid for vid, _, _ in active_vehicle_routes}
    for stale_id in list(_vehicle_last_route_percent.keys()):
        if stale_id not in active_vehicle_ids:
            _vehicle_last_route_percent.pop(stale_id, None)
            _vehicle_last_is_forward.pop(stale_id, None)

    async with AsyncSessionLocal() as db:
        place_node_map = await get_primary_node_id_per_place(db, place_ids)
        latest_locations = await _get_latest_vehicle_locations(db, vehicle_ids)

        updates: list[dict[str, Any]] = []
        for vehicle_id, place_a_id, place_b_id in active_vehicle_routes:
            start_node_id = place_node_map.get(place_a_id)
            target_node_id = place_node_map.get(place_b_id)
            location = latest_locations.get(vehicle_id)
            progress_percent = 50.0
            location_known = False
            distance_remaining_m = None
            progress_time = None

            if start_node_id is not None and target_node_id is not None and location is not None:
                route_data = await _get_route_data(start_node_id, target_node_id, db)
                if route_data is not None:
                    try:
                        progress = await loc_finder.calculate_route_progress(
                            route_data,
                            location["lat"],
                            location["lon"],
                            db,
                        )
                        progress_percent = _clamp_progress(progress.get("percent_complete"))
                        distance_remaining_m = progress.get("distance_remaining_m")
                        progress_time = await loc_finder.calculate_time_to_destination(
                            distance_remaining_m,
                        )
                        location_known = True
                    except Exception as exc:
                        logger.warning(
                            "Failed to calculate route progress: "
                            "vehicle_id=%s place_a=%s place_b=%s error=%s",
                            vehicle_id,
                            place_a_id,
                            place_b_id,
                            exc,
                            exc_info=True,
                        )

            is_moving_forward: bool | None = None
            if location_known:
                prev_pct = _vehicle_last_route_percent.get(vehicle_id)
                if prev_pct is not None:
                    delta = progress_percent - prev_pct
                    if abs(delta) >= _PROGRESS_DELTA_EPSILON_PCT:
                        _vehicle_last_is_forward[vehicle_id] = delta > 0
                known_dir = _vehicle_last_is_forward.get(vehicle_id)
                is_moving_forward = known_dir
                _vehicle_last_route_percent[vehicle_id] = progress_percent

            updates.append(
                {
                    "event_type": "route_progress",
                    "vehicle_id": vehicle_id,
                    "place_a_id": place_a_id,
                    "place_b_id": place_b_id,
                    "route_key": f"{place_a_id}-{place_b_id}",
                    "start_node_id": start_node_id,
                    "target_node_id": target_node_id,
                    "progress_percent": round(progress_percent, 2),
                    "is_moving_forward": is_moving_forward,
                    "location_known": location_known,
                    "lat": location["lat"] if location is not None else None,
                    "lon": location["lon"] if location is not None else None,
                    "timestamp": timestamp,
                    "distance_remaining_m": distance_remaining_m
                    if distance_remaining_m is not None
                    else None,
                    "minutes_to_destination": progress_time["minutes"]
                    if progress_time is not None
                    else None,
                },
            )

        return updates


async def route_progress_stream(request: Request) -> AsyncGenerator[str]:
    """Emit one live route-progress message with all vehicles every second."""
    logger.info("SSE route progress client connected")

    try:
        yield f"data: {json.dumps({'type': 'connected', 'stream': 'route_progress'})}\n\n"
    except Exception as exc:
        logger.error("SSE route progress: failed to send connected event", error=str(exc))
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        return

    try:
        while True:
            try:
                if await request.is_disconnected():
                    logger.info("SSE route progress client disconnected")
                    break
            except Exception as exc:
                logger.warning("SSE route progress: is_disconnected check failed", error=str(exc))
                break

            try:
                updates = await build_route_progress_updates()
                if updates:
                    # Один SSE payload на весь фронт за тик.
                    vehicles_map = {
                        str(u.get("vehicle_id")): u
                        for u in updates
                        if u.get("vehicle_id") is not None
                    }
                    yield f"data: {json.dumps(vehicles_map)}\n\n"
                else:
                    yield ": heartbeat\n\n"
            except Exception as exc:
                logger.error("Route progress SSE stream iteration failed", error=str(exc))
                yield ": heartbeat\n\n"

            await asyncio.sleep(1)
    finally:
        logger.info("SSE route progress connection closed")


async def routes_progress_stream(request: Request) -> AsyncGenerator[str]:
    """SSE stream for /api/events/stream/routes.

    Формат сообщений (раз в секунду, одним payload):
    [
      { "event_type": "route_progress", "vehicle_id": 4, ... },
      { "event_type": "route_progress", "vehicle_id": 17, ... }
    ]
    """
    logger.info("SSE routes progress client connected")

    try:
        yield f"data: {json.dumps({'type': 'connected', 'stream': 'routes_progress'})}\n\n"
    except Exception as exc:
        logger.error("SSE routes progress: failed to send connected event", error=str(exc))
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        return

    try:
        while True:
            try:
                if await request.is_disconnected():
                    logger.info("SSE routes progress client disconnected")
                    break
            except Exception as exc:
                logger.warning("SSE routes progress: is_disconnected check failed", error=str(exc))
                break

            try:
                updates = await build_route_progress_updates()
                if updates:
                    items: list[dict[str, Any]] = []
                    for update in updates:
                        vehicle_id = update.get("vehicle_id")
                        place_a_id = update.get("place_a_id")
                        place_b_id = update.get("place_b_id")
                        if vehicle_id is None or place_a_id is None or place_b_id is None:
                            continue
                        try:
                            vid_int = int(vehicle_id)
                        except (TypeError, ValueError):
                            continue

                        progress_percent = update.get("progress_percent", 50.0)
                        state = get_vehicle_state(vid_int) or "no_data"

                        payload = {
                            "event_type": "route_progress",
                            "vehicle_id": vid_int,
                            "progress_percent": progress_percent,
                            "distance_remaining_m": update.get("distance_remaining_m"),
                            "minutes_to_destination": update.get("minutes_to_destination"),
                            "is_moving_forward": update.get("is_moving_forward"),
                            "state": state,
                        }
                        items.append(payload)

                    if items:
                        yield f"data: {json.dumps(items)}\n\n"
                    else:
                        yield ": heartbeat\n\n"
                else:
                    yield ": heartbeat\n\n"
            except Exception as exc:
                logger.error("Routes progress SSE iteration failed", error=str(exc))
                yield ": heartbeat\n\n"

            await asyncio.sleep(1)
    finally:
        logger.info("SSE routes progress connection closed")
