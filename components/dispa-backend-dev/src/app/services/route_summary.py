"""Сервис для формирования сводки маршрутов текущей смены.

Логика:
1. Определить текущую смену (shift_date, shift_num) через enterprise-service.
2. Получить и закэшировать границы смены (start_time, end_time) через get_shift_time_range.
3. Загрузить все ShiftTask текущей смены вместе с route_tasks (selectin).
4. Сгруппировать route_tasks по уникальному маршруту (place_a_id, place_b_id).
5. Для каждого маршрута:
   - volume_plan  = SUM(route_task.volume)
   - volume_fact  = определяется по рейсам (Trip) за смену:
                    JOIN trips с place_remaining_history по cycle_id,
                    GROUP BY (loading_place_id, unloading_place_id),
                    SUM(ABS(change_volume)) по unloading-записям
                    в интервале [start_time, end_time) смены.
   - active_vehicles = vehicle_id из shift_task, где route_task.status == ACTIVE
"""

import asyncio
import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

import httpx
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas.route_summary import (
    DispatcherAssignmentCreateRequest,
    DispatcherAssignmentResponse,
    FleetControlResponse,
    FleetGarageItem,
    FleetRouteSummaryItem,
    FleetVehicle,
    RouteSummaryItem,
    RouteSummaryResponse,
    RouteTemplateCreateRequest,
    RouteTemplateResponse,
    RouteTemplateUpdateRequest,
    UnusedVehiclesResponse,
)
from app.core.config import settings
from app.core.redis_client import redis_client
from app.database.models import (
    CycleStateHistory,
    DispatcherAssignment,
    PlaceRemainingHistory,
    RouteTask,
    ShiftRouteTemplate,
    ShiftTask,
    Trip,
)
from app.enums import (
    DispatcherAssignmentKindEnum,
    DispatcherAssignmentStatusEnum,
    RemainingChangeTypeEnum,
)
from app.enums.route_tasks import TripStatusRouteEnum
from app.services.enterprise_client import enterprise_client
from app.services.place_info import get_place
from app.services.trip_state_sync_service import get_shift_time_range


async def _get_current_shift_info() -> dict[str, Any] | None:
    """Запрашивает у enterprise-service информацию о текущей смене.

    Получает shift_date и shift_num по текущему timestamp.
    """
    try:
        now_utc = datetime.now(UTC).replace(tzinfo=None)
        url = f"{settings.enterprise_service_url}/api/shift-service/get-shift-info-by-timestamp"
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params={"timestamp": now_utc.isoformat()})
            if response.status_code == 200:
                return response.json()
            logger.warning(
                "Failed to get current shift info",
                status_code=response.status_code,
                body=response.text,
            )
    except Exception as e:
        logger.error("Error getting current shift info", error=str(e), exc_info=True)
    return None


_cached_shift_time_range: dict[str, datetime] | None = None
_cached_shift_time_range_key: tuple[str, int] | None = None

# Кеш маппинга horizon_id -> section_ids для вычисления section_ids маршрутов.
_horizon_to_section_id_cache: dict[int, set[int]] | None = None
# Кеш маппинга place_id -> horizon_id (полезно для section_id).
_place_to_horizon_id_cache: dict[int, int | None] = {}

# Кэш длины маршрута для fleet-control: (place_a_id, place_b_id) -> (length_m, monotonic_ts)
_fleet_route_length_m_cache: dict[tuple[int, int], tuple[float, float]] = {}

# Кэш списка всех park-мест (для заполнения garages пустыми массивами)
_park_places_cache: tuple[float, list[dict[str, Any]]] | None = None
_park_place_ids_cache_ttl_seconds = 300.0


async def _get_all_park_places() -> list[dict[str, Any]]:
    global _park_places_cache
    now_m = time.monotonic()
    if _park_places_cache is not None:
        cached_at, cached_items = _park_places_cache
        if now_m - cached_at < _park_place_ids_cache_ttl_seconds:
            return cached_items

    url = f"{settings.graph_service_url}/api/places"
    try:
        async with httpx.AsyncClient(timeout=settings.enterprise_http_timeout_seconds) as client:
            resp = await client.get(
                url,
                params={
                    "types": "park",
                    "is_active": "true",
                    "limit": 1000,
                    "offset": 0,
                },
            )
            resp.raise_for_status()
            payload = resp.json()
    except Exception as e:
        logger.warning(
            "Failed to fetch park place ids for fleet-control",
            error=str(e),
            url=url,
        )
        return []

    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []

    parks: list[dict[str, Any]] = []
    for p in items:
        if not isinstance(p, dict):
            continue
        pid = p.get("id")
        if pid is None:
            continue
        try:
            pid_int = int(pid)
        except (TypeError, ValueError):
            continue
        name_raw = p.get("name")
        parks.append({"id": pid_int, "name": str(name_raw) if name_raw is not None else f"#{pid_int}"})

    # dedupe while preserving order
    seen: set[int] = set()
    deduped: list[dict[str, Any]] = []
    for park in parks:
        pid = int(park["id"])
        if pid in seen:
            continue
        seen.add(pid)
        deduped.append(park)

    _park_places_cache = (now_m, deduped)
    return deduped


async def _batch_resolve_graph_nodes_for_places(place_ids: set[int]) -> dict[int, int]:
    if not place_ids:
        return {}
    params = httpx.QueryParams([("place_ids", str(pid)) for pid in sorted(place_ids)])
    url = f"{settings.graph_service_url}/api/route/place-node-ids"
    try:
        async with httpx.AsyncClient(timeout=settings.enterprise_http_timeout_seconds) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception as e:
        logger.warning(
            "Failed to resolve graph nodes for places",
            error=str(e),
            place_ids=sorted(place_ids),
        )
        return {}
    nodes = payload.get("nodes") if isinstance(payload, dict) else None
    if not isinstance(nodes, dict):
        return {}
    result: dict[int, int] = {}
    for k, v in nodes.items():
        try:
            result[int(k)] = int(v)
        except (TypeError, ValueError):
            continue
    return result


async def _get_route_length_m_cached(
    place_a_id: int,
    place_b_id: int,
    start_node_id: int | None,
    target_node_id: int | None,
) -> float | None:
    if start_node_id is None or target_node_id is None:
        return None
    key = (place_a_id, place_b_id)
    now_m = time.monotonic()
    ttl = settings.fleet_route_length_cache_ttl_seconds
    cached = _fleet_route_length_m_cache.get(key)
    if cached is not None:
        length_m, cached_at = cached
        if now_m - cached_at < ttl:
            return length_m
    url = f"{settings.graph_service_url}/api/route/{start_node_id}/{target_node_id}"
    try:
        async with httpx.AsyncClient(timeout=settings.enterprise_http_timeout_seconds) as client:
            response = await client.get(url)
            if response.status_code != 200:
                logger.warning(
                    "Graph route length request failed",
                    status_code=response.status_code,
                    url=url,
                    body=(response.text[:200] if response.text else None),
                )
                return None
            data = response.json()
            if not isinstance(data, dict):
                return None
            raw_len = data.get("total_length_m")
            if raw_len is None:
                return None
            length_m = float(raw_len)
    except Exception as e:
        logger.warning(
            "Failed to fetch route length from graph-service",
            error=str(e),
            place_a_id=place_a_id,
            place_b_id=place_b_id,
        )
        return None
    _fleet_route_length_m_cache[key] = (length_m, now_m)
    return length_m


async def _get_cached_shift_time_range(
    shift_date: str,
    shift_num: int,
) -> dict[str, datetime] | None:
    """Получить границы смены с кешированием по (shift_date, shift_num)."""
    global _cached_shift_time_range, _cached_shift_time_range_key

    key = (shift_date, shift_num)
    if _cached_shift_time_range_key == key and _cached_shift_time_range is not None:
        return _cached_shift_time_range

    shift_time_range = await get_shift_time_range(shift_date=shift_date, shift_num=shift_num)
    if shift_time_range is not None:
        _cached_shift_time_range = shift_time_range
        _cached_shift_time_range_key = key
    else:
        _cached_shift_time_range = None
        _cached_shift_time_range_key = None

    return shift_time_range


async def get_route_summary(db: AsyncSession) -> RouteSummaryResponse:
    """Основной метод: возвращает RouteSummaryResponse с агрегированными маршрутами."""
    # 1. Определяем текущую смену
    shift_info = await _get_current_shift_info()
    if not shift_info:
        logger.warning("Current shift not determined — returning empty summary")
        return RouteSummaryResponse(shift_date=None, shift_num=None, routes=[])

    shift_date: str = shift_info["shift_date"]
    shift_num: int = shift_info["shift_num"]

    # 2. Получаем границы смены (с кешированием)
    shift_time_range = await _get_cached_shift_time_range(
        shift_date=shift_date,
        shift_num=shift_num,
    )
    if not shift_time_range:
        logger.warning(
            "Shift time range not determined — returning empty summary",
            shift_date=shift_date,
            shift_num=shift_num,
        )
        return RouteSummaryResponse(shift_date=shift_date, shift_num=shift_num, routes=[])

    shift_start: datetime = shift_time_range["start_time"]
    shift_end: datetime = shift_time_range["end_time"]

    # 3. Загружаем ShiftTask текущей смены (route_tasks подтянутся через selectin)
    query = select(ShiftTask).where(
        ShiftTask.shift_date == shift_date,
        ShiftTask.shift_num == shift_num,
    )
    result = await db.execute(query)
    shift_tasks: list[ShiftTask] = list(result.scalars().all())

    # Маппинг shift_task_id -> vehicle_id (для active_vehicles)
    st_vehicle: dict[str, int] = {str(st.id): st.vehicle_id for st in shift_tasks}

    # 4. Собираем route_tasks и группируем по (place_a_id, place_b_id)
    RouteKey = tuple[int, int]
    grouped_volume: dict[RouteKey, float] = defaultdict(float)
    grouped_task_ids: dict[RouteKey, list[str]] = defaultdict(list)
    grouped_active_vehicles: dict[RouteKey, set[int]] = defaultdict(set)
    grouped_pending_vehicles: dict[RouteKey, set[int]] = defaultdict(set)

    for st in shift_tasks:
        for rt in st.route_tasks or []:
            # Пропускаем отклонённые наряд-задания
            if rt.status == TripStatusRouteEnum.REJECTED:
                continue

            key: RouteKey = (rt.place_a_id, rt.place_b_id)
            grouped_volume[key] += rt.volume or 0.0
            grouped_task_ids[key].append(str(rt.id))

            if rt.status == TripStatusRouteEnum.ACTIVE:
                vehicle_id = st_vehicle.get(str(rt.shift_task_id))
                if vehicle_id:
                    grouped_active_vehicles[key].add(vehicle_id)

    # Pending назначения диспетчера для текущей смены.
    # Используем их для:
    # - показа техники полупрозрачной на целевом маршруте (target_kind=route)
    # - скрытия техники с исходного маршрута (source_kind=route), даже если route_task ещё ACTIVE.
    assignments_query = select(DispatcherAssignment).where(
        DispatcherAssignment.shift_date == shift_date,
        DispatcherAssignment.shift_num == shift_num,
        DispatcherAssignment.status == DispatcherAssignmentStatusEnum.PENDING.value,
    )
    assignments_result = await db.execute(assignments_query)
    assignments: list[DispatcherAssignment] = list(assignments_result.scalars().all())
    pending_by_vehicle: dict[int, DispatcherAssignment] = {}
    for a in assignments:
        vehicle_id_int = int(a.vehicle_id)
        pending_by_vehicle[vehicle_id_int] = a

        # Если цель — маршрут, показываем технику как pending на целевом маршруте
        if (
            a.target_kind == DispatcherAssignmentKindEnum.ROUTE.value
            and a.target_route_place_a_id is not None
            and a.target_route_place_b_id is not None
        ):
            grouped_pending_vehicles[(int(a.target_route_place_a_id), int(a.target_route_place_b_id))].add(
                vehicle_id_int,
            )

        # Если источник — маршрут, скрываем технику с исходного маршрута,
        # даже если её route_task пока ещё ACTIVE.
        if (
            a.source_kind == DispatcherAssignmentKindEnum.ROUTE.value
            and a.source_route_place_a_id is not None
            and a.source_route_place_b_id is not None
        ):
            src_key: RouteKey = (int(a.source_route_place_a_id), int(a.source_route_place_b_id))
            if src_key in grouped_active_vehicles:
                grouped_active_vehicles[src_key].discard(vehicle_id_int)

    # Если у техники есть pending assignment — показываем её только в target (а не на других маршрутах).
    # Исключение: target_kind=ROUTE — она отображается как pending на target маршруте.
    if pending_by_vehicle:
        for vehicle_id_int, a in pending_by_vehicle.items():
            # убрать из active везде
            for active_set in grouped_active_vehicles.values():
                active_set.discard(vehicle_id_int)
            # убрать из pending везде, затем добавить только в target (если target=route)
            for pending_set in grouped_pending_vehicles.values():
                pending_set.discard(vehicle_id_int)
            if (
                a.target_kind == DispatcherAssignmentKindEnum.ROUTE.value
                and a.target_route_place_a_id is not None
                and a.target_route_place_b_id is not None
            ):
                grouped_pending_vehicles[(int(a.target_route_place_a_id), int(a.target_route_place_b_id))].add(
                    vehicle_id_int,
                )

    # 5. Добавляем в агрегаты пустые маршруты из шаблонов текущей смены
    templates_query = select(ShiftRouteTemplate).where(
        ShiftRouteTemplate.shift_date == shift_date,
        ShiftRouteTemplate.shift_num == shift_num,
    )
    templates_result = await db.execute(templates_query)
    templates: list[ShiftRouteTemplate] = list(templates_result.scalars().all())

    for tmpl in templates:
        tmpl_key: RouteKey = (tmpl.place_a_id, tmpl.place_b_id)
        if tmpl_key not in grouped_volume:
            grouped_volume[tmpl_key] = 0.0
            grouped_task_ids[tmpl_key] = []
            grouped_active_vehicles[tmpl_key] = set()

    # 6. Считаем volume_fact по рейсам текущей смены
    #    (группируем рейсы по loading_place_id/unloading_place_id, далее суммируем unloading из place_remaining_history
    #    в интервале [shift_start, shift_end))
    volume_fact_by_route = await _calc_volume_fact_by_trips(
        db=db,
        shift_start=shift_start,
        shift_end=shift_end,
    )

    # 7. Формируем результат
    routes: list[RouteSummaryItem] = []
    for key in sorted(grouped_volume.keys()):
        place_a, place_b = key
        routes.append(
            RouteSummaryItem(
                place_a_id=place_a,
                place_b_id=place_b,
                volume_plan=round(grouped_volume[key], 1),
                volume_fact=round(volume_fact_by_route.get(key, 0.0), 1),
                active_vehicles=sorted(grouped_active_vehicles.get(key, set())),
                pending_vehicles=sorted(grouped_pending_vehicles.get(key, set())),
                route_task_ids=grouped_task_ids[key],
            ),
        )

    return RouteSummaryResponse(
        shift_date=shift_date,
        shift_num=shift_num,
        routes=routes,
    )


async def _get_vehicle_name_map(vehicle_ids: set[int]) -> tuple[dict[int, str], dict[int, str | None]]:
    """Получить имена и vehicle_type техники по заданному набору id (из enterprise-service)."""
    if not vehicle_ids:
        return {}, {}

    try:
        active_vehicles = await enterprise_client.get_active_vehicles()
    except Exception as e:
        logger.warning("Failed to fetch vehicle names", error=str(e))
        active_vehicles = []

    name_by_id: dict[int, str] = {}
    type_by_id: dict[int, str | None] = {}
    for v in active_vehicles:
        raw_id = v.get("id")
        if raw_id is None:
            continue
        try:
            vid = int(raw_id)
        except (TypeError, ValueError) as e:
            logger.warning("Failed to parse vehicle id", raw_id=raw_id, error=str(e))
            continue
        if vid not in vehicle_ids:
            continue
        name = v.get("name") or v.get("registration_number") or v.get("serial_number")
        name_by_id[vid] = str(name) if name is not None else f"#{vid}"
        vehicle_type = v.get("vehicle_type")
        type_by_id[vid] = str(vehicle_type) if vehicle_type is not None else None
    return name_by_id, type_by_id


async def _get_latest_cycle_state_map(
    db: AsyncSession,
    vehicle_ids: set[int],
    before_timestamp: datetime,
) -> dict[int, CycleStateHistory]:
    """Получить последние записи cycle_state_history для набора техники."""
    if not vehicle_ids:
        return {}

    subq = (
        select(
            CycleStateHistory.vehicle_id,
            func.max(CycleStateHistory.timestamp).label("max_ts"),
        )
        .where(CycleStateHistory.vehicle_id.in_(vehicle_ids))
        .where(CycleStateHistory.timestamp <= before_timestamp)
        .group_by(CycleStateHistory.vehicle_id)
        .subquery()
    )

    query = select(CycleStateHistory).join(
        subq,
        (CycleStateHistory.vehicle_id == subq.c.vehicle_id) & (CycleStateHistory.timestamp == subq.c.max_ts),
    )
    result = await db.execute(query)
    records = result.scalars().all()
    return {r.vehicle_id: r for r in records}


async def _ensure_horizon_to_section_id_map_loaded() -> dict[int, set[int]]:
    global _horizon_to_section_id_cache
    if _horizon_to_section_id_cache is not None:
        return _horizon_to_section_id_cache

    mapping: dict[int, set[int]] = {}
    url = f"{settings.graph_service_url}/api/sections"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as e:
        logger.warning(
            "Failed to load sections from graph-service",
            error=str(e),
            url=url,
        )
        _horizon_to_section_id_cache = None
        return {}

    items: Any = None
    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("data") or payload.get("results")
    elif isinstance(payload, list):
        items = payload

    if not isinstance(items, list) or not items:
        logger.warning(
            "Unexpected /api/sections response shape",
            url=url,
            payload_type=type(payload).__name__,
            has_items=isinstance(payload, dict) and ("items" in payload),
            keys=list(payload.keys()) if isinstance(payload, dict) else None,
        )
        _horizon_to_section_id_cache = None
        return {}

    for sec in items:
        sec_id = sec.get("id")
        if sec_id is None:
            continue
        try:
            section_id = int(sec_id)
        except (TypeError, ValueError) as e:
            logger.warning("Failed to parse section id", sec_id=sec_id, error=str(e))
            continue
        horizons = sec.get("horizons") or []
        for h in horizons:
            if isinstance(h, dict):
                hid = h.get("id")
            else:
                hid = h
            if hid is None:
                continue
            try:
                horizon_id = int(hid)
            except (TypeError, ValueError) as e:
                logger.warning(
                    "Failed to parse horizon id",
                    hid=hid,
                    error=str(e),
                )
                continue
            mapping.setdefault(horizon_id, set()).add(section_id)

    _horizon_to_section_id_cache = mapping
    return mapping


async def _get_section_ids_for_place(place_id: int) -> list[int]:
    """Вычислить section_ids для места через его horizon_id."""
    if place_id in _place_to_horizon_id_cache:
        horizon_id = _place_to_horizon_id_cache[place_id]
    else:
        place_info = await get_place(place_id)
        horizon_id_raw = (place_info or {}).get("horizon_id") if isinstance(place_info, dict) else None
        horizon_id = int(horizon_id_raw) if horizon_id_raw is not None else None
        _place_to_horizon_id_cache[place_id] = horizon_id

    if horizon_id is None:
        return []

    horizon_to_section = await _ensure_horizon_to_section_id_map_loaded()
    section_ids = horizon_to_section.get(horizon_id)
    return sorted(section_ids) if section_ids else []


async def get_fleet_control(db: AsyncSession) -> FleetControlResponse:
    """Единый эндпоинт для страницы управления техникой.

    Возвращает:
    - сводку маршрутов текущей смены (routes, shift_date/shift_num)
    - незадействованную технику (no_task/garages/idle), без отдельного pending_garages
    """
    summary = await get_route_summary(db)
    unused = await get_unused_vehicles(db)

    if summary.shift_date is None or summary.shift_num is None:
        return FleetControlResponse(shift_date=None, shift_num=None, routes=[], no_task=[], garages=[], idle=[])

    shift_time_range = await _get_cached_shift_time_range(shift_date=summary.shift_date, shift_num=summary.shift_num)
    shift_end = shift_time_range["end_time"] if shift_time_range else datetime.now(UTC).replace(tzinfo=None)

    route_vehicle_ids: set[int] = set()
    for r in summary.routes:
        route_vehicle_ids.update(r.active_vehicles)
        route_vehicle_ids.update(r.pending_vehicles)

    unused_vehicle_ids: set[int] = set(unused.no_task)
    for v_list in unused.garages.values():
        unused_vehicle_ids.update(v_list)
    for v_list in unused.pending_garages.values():
        unused_vehicle_ids.update(v_list)
    unused_vehicle_ids.update(unused.idle)

    all_vehicle_ids = route_vehicle_ids | unused_vehicle_ids

    name_by_id, vehicle_type_by_id = await _get_vehicle_name_map(all_vehicle_ids)
    state_by_id = await _get_latest_cycle_state_map(db, all_vehicle_ids, before_timestamp=shift_end)

    def make_vehicle(vehicle_id: int, is_assigned: bool) -> FleetVehicle:
        st = state_by_id.get(vehicle_id)
        state_value = st.state if st else "no_data"
        return FleetVehicle(
            id=vehicle_id,
            name=name_by_id.get(vehicle_id, f"#{vehicle_id}"),
            state=state_value,
            is_assigned=is_assigned,
            vehicle_type=vehicle_type_by_id.get(vehicle_id) or "-",
        )

    # section_ids считаем по ПП (place_a_id) для каждого маршрута
    place_a_ids = {r.place_a_id for r in summary.routes}
    section_ids_by_place_a: dict[int, list[int]] = {}
    if place_a_ids:
        place_a_id_list = sorted(place_a_ids)
        section_results = await asyncio.gather(*[_get_section_ids_for_place(pid) for pid in place_a_id_list])
        for pid, section_ids in zip(place_a_id_list, section_results, strict=False):
            section_ids_by_place_a[pid] = section_ids

    route_place_ids: set[int] = set()
    for r in summary.routes:
        route_place_ids.add(r.place_a_id)
        route_place_ids.add(r.place_b_id)
    graph_node_by_place = await _batch_resolve_graph_nodes_for_places(route_place_ids)

    async def _route_length_for_row(row: RouteSummaryItem) -> float | None:
        return await _get_route_length_m_cached(
            row.place_a_id,
            row.place_b_id,
            graph_node_by_place.get(row.place_a_id),
            graph_node_by_place.get(row.place_b_id),
        )

    route_length_by_idx: list[float | None] = (
        list(await asyncio.gather(*[_route_length_for_row(r) for r in summary.routes])) if summary.routes else []
    )

    fleet_routes: list[FleetRouteSummaryItem] = []
    for idx, r in enumerate(summary.routes):
        active_set = set(r.active_vehicles)
        vehicles: list[FleetVehicle] = []
        vehicles.extend([make_vehicle(vid, is_assigned=True) for vid in r.active_vehicles])
        for vid in r.pending_vehicles:
            if vid in active_set:
                continue
            vehicles.append(make_vehicle(vid, is_assigned=False))

        fleet_routes.append(
            FleetRouteSummaryItem(
                place_a_id=r.place_a_id,
                place_b_id=r.place_b_id,
                route_id=f"{r.place_a_id}-{r.place_b_id}",
                section_ids=section_ids_by_place_a.get(r.place_a_id, []),
                volume_plan=r.volume_plan,
                volume_fact=r.volume_fact,
                vehicles=vehicles,
                route_task_ids=r.route_task_ids,
                route_length_m=route_length_by_idx[idx] if idx < len(route_length_by_idx) else None,
            ),
        )

    # В `no_task`/`idle` нет PENDING dispatcher_assignments, поэтому is_assigned=true.
    no_task_objects = sorted(
        (make_vehicle(vid, is_assigned=True) for vid in unused.no_task),
        key=lambda v: v.name,
    )

    garages_objects: dict[int, dict[int, FleetVehicle]] = defaultdict(dict)
    # Базовые гаражи (обычное нахождение): is_assigned=true
    for park_id, v_ids in unused.garages.items():
        garages_objects[park_id].update({vid: make_vehicle(vid, is_assigned=True) for vid in v_ids})
    # Pending-гаражи (pending-назначение диспетчера): is_assigned=false
    for park_id, v_ids in unused.pending_garages.items():
        for vid in v_ids:
            garages_objects[park_id][vid] = make_vehicle(vid, is_assigned=False)

    garages_by_id: dict[int, list[FleetVehicle]] = {
        park_id: sorted(vehicles_by_id.values(), key=lambda v: v.name)
        for park_id, vehicles_by_id in garages_objects.items()
    }

    # Заполняем garages всеми park-местами даже при отсутствии техники.
    park_places = await _get_all_park_places()
    garages: list[FleetGarageItem] = [
        FleetGarageItem(
            id=int(park["id"]),
            name=str(park["name"]),
            vehicles=garages_by_id.get(int(park["id"]), []),
        )
        for park in park_places
    ]

    idle_objects = sorted(
        (make_vehicle(vid, is_assigned=True) for vid in unused.idle),
        key=lambda v: v.name,
    )

    return FleetControlResponse(
        shift_date=summary.shift_date,
        shift_num=summary.shift_num,
        routes=fleet_routes,
        no_task=no_task_objects,
        garages=garages,
        idle=idle_objects,
    )


async def get_unused_vehicles(db: AsyncSession) -> UnusedVehiclesResponse:
    """Незадействованная техника текущей смены: нет активного наряд-задания.

    - no_task: техника в смене, у которой ни один route_task не в статусе ACTIVE.
    - garage_zone: подмножество no_task, у которой последнее место (last_place_id из Redis) имеет тип park.
    - idle: подмножество no_task, у которой текущее состояние (state из Redis) не is_work_status.
    """
    shift_info = await _get_current_shift_info()
    if not shift_info:
        return UnusedVehiclesResponse(no_task=[], garages={}, pending_garages={}, idle=[])

    shift_date = shift_info["shift_date"]
    shift_num = int(shift_info["shift_num"])

    query = select(ShiftTask).where(
        ShiftTask.shift_date == shift_date,
        ShiftTask.shift_num == shift_num,
    )
    result = await db.execute(query)
    shift_tasks: list[ShiftTask] = list(result.scalars().all())
    try:
        active_vehicles = await enterprise_client.get_active_vehicles()
    except Exception as e:
        logger.warning("Failed to fetch active vehicles for fleet-control", error=str(e))
        active_vehicles = []

    parsed_vehicle_ids: set[int] = set()
    for v in active_vehicles:
        raw_id = v.get("id")
        if raw_id is None:
            continue
        try:
            parsed_vehicle_ids.add(int(raw_id))
        except (TypeError, ValueError):
            continue

    all_vehicle_ids: set[int] = parsed_vehicle_ids or {st.vehicle_id for st in shift_tasks}
    active_vehicle_ids: set[int] = set()
    for st in shift_tasks:
        for rt in st.route_tasks or []:
            if rt.status == TripStatusRouteEnum.REJECTED:
                continue
            if rt.status == TripStatusRouteEnum.ACTIVE:
                active_vehicle_ids.add(st.vehicle_id)
                break

    # Техника с pending-назначением показывается только в target этого назначения
    # (маршрут/гараж/нет задания). Исключение: idle — показываем всегда.
    pending_any_query = select(DispatcherAssignment).where(
        DispatcherAssignment.shift_date == shift_date,
        DispatcherAssignment.shift_num == shift_num,
        DispatcherAssignment.status == DispatcherAssignmentStatusEnum.PENDING.value,
    )
    pending_any_result = await db.execute(pending_any_query)
    pending_any: list[DispatcherAssignment] = list(pending_any_result.scalars().all())
    pending_by_vehicle: dict[int, DispatcherAssignment] = {int(a.vehicle_id): a for a in pending_any}

    vehicles_with_pending = set(pending_by_vehicle.keys())
    pending_to_no_task: set[int] = {
        vid for vid, a in pending_by_vehicle.items() if a.target_kind == DispatcherAssignmentKindEnum.NO_TASK.value
    }

    no_task_ids = sorted((all_vehicle_ids - active_vehicle_ids - vehicles_with_pending) | pending_to_no_task)
    if not no_task_ids:
        return UnusedVehiclesResponse(no_task=[], garages={}, pending_garages={}, idle=[])

    try:
        statuses = await enterprise_client.get_all_statuses()
    except Exception as e:
        logger.warning("Failed to get statuses for unused vehicles", error=str(e))
        statuses = []
    status_work_map = {str(s.get("system_name", "")): bool(s.get("is_work_status", False)) for s in statuses}

    garages: dict[int, list[int]] = defaultdict(list)
    idle_ids: list[int] = []

    place_type_cache: dict[int, str] = {}

    # Idle считаем по всей технике (включая pending).
    for vehicle_id in sorted(all_vehicle_ids):
        state_data: dict[str, Any] | None = None
        if redis_client.redis is not None:
            try:
                state_data = await redis_client.get_state_machine_data(str(vehicle_id))
            except Exception as e:
                logger.debug("Redis get_state_machine_data failed", vehicle_id=vehicle_id, error=str(e))

        # В «В простое» только если в Redis есть явное состояние и оно не is_work_status.
        # При отсутствии данных в Redis не считаем технику в простое (она может работать).
        current_state = (state_data or {}).get("state") if state_data else None
        if current_state is not None:
            is_work = status_work_map.get(str(current_state), False)
            if not is_work:
                idle_ids.append(vehicle_id)

        # no_task/garages строим только по no_task_ids, исключая pending (кроме target_kind=NO_TASK).
        if vehicle_id not in no_task_ids:
            continue
        if vehicle_id in vehicles_with_pending and vehicle_id not in pending_to_no_task:
            continue

        last_place_id = (state_data or {}).get("last_place_id")
        if last_place_id is not None:
            lp = int(last_place_id)
            if lp not in place_type_cache:
                place_info = await get_place(lp)
                place_type_cache[lp] = str((place_info or {}).get("type", "")).lower()
            if place_type_cache.get(lp) == "park":
                garages[lp].append(vehicle_id)

    # Pending назначения диспетчера в конкретные гаражи
    pending_garages: dict[int, list[int]] = defaultdict(list)
    pending_query = select(DispatcherAssignment).where(
        DispatcherAssignment.shift_date == shift_date,
        DispatcherAssignment.shift_num == shift_num,
        DispatcherAssignment.status == DispatcherAssignmentStatusEnum.PENDING.value,
        DispatcherAssignment.target_kind == DispatcherAssignmentKindEnum.GARAGE.value,
    )
    pending_result = await db.execute(pending_query)
    pending_assignments: list[DispatcherAssignment] = list(pending_result.scalars().all())
    for a in pending_assignments:
        if a.target_garage_place_id is None:
            continue
        pending_garages[int(a.target_garage_place_id)].append(int(a.vehicle_id))

    return UnusedVehiclesResponse(
        no_task=no_task_ids,
        garages={int(k): v for k, v in garages.items()},
        pending_garages={int(k): v for k, v in pending_garages.items()},
        idle=idle_ids,
    )


def _validate_assignment_payload(body: DispatcherAssignmentCreateRequest) -> None:
    source_kind = (body.source_kind or "").upper()
    target_kind = (body.target_kind or "").upper()

    if source_kind not in {e.value for e in DispatcherAssignmentKindEnum}:
        raise ValueError("source_kind must be one of: ROUTE, NO_TASK, GARAGE")
    if target_kind not in {e.value for e in DispatcherAssignmentKindEnum}:
        raise ValueError("target_kind must be one of: ROUTE, NO_TASK, GARAGE")

    if source_kind == DispatcherAssignmentKindEnum.ROUTE.value:
        if body.source_route_place_a_id is None or body.source_route_place_b_id is None:
            raise ValueError("source_route_place_a_id/source_route_place_b_id required for source_kind=route")
    if source_kind == DispatcherAssignmentKindEnum.GARAGE.value:
        if body.source_garage_place_id is None:
            raise ValueError("source_garage_place_id required for source_kind=garage")

    if target_kind == DispatcherAssignmentKindEnum.ROUTE.value:
        if body.target_route_place_a_id is None or body.target_route_place_b_id is None:
            raise ValueError("target_route_place_a_id/target_route_place_b_id required for target_kind=route")
    if target_kind == DispatcherAssignmentKindEnum.GARAGE.value:
        if body.target_garage_place_id is None:
            raise ValueError("target_garage_place_id required for target_kind=garage")


async def create_or_update_dispatcher_assignment(
    body: DispatcherAssignmentCreateRequest,
    db: AsyncSession,
) -> DispatcherAssignmentResponse:
    """Создать или обновить pending-назначение диспетчера для текущей смены."""
    _validate_assignment_payload(body)

    shift_info = await _get_current_shift_info()
    if not shift_info:
        raise ValueError("Current shift not determined")
    shift_date: str = shift_info["shift_date"]
    shift_num: int = int(shift_info["shift_num"])

    target_kind_normalized = (body.target_kind or "").upper()

    # Специальный кейс: перенос в NO_TASK выполняется сразу, без pending-assignment.
    if target_kind_normalized == DispatcherAssignmentKindEnum.NO_TASK.value:
        # Если у техники есть PENDING назначение диспетчера в этой смене — отклоняем его,
        # иначе оно будет мешать отображению/поведению в UI.
        pending_res = await db.execute(
            select(DispatcherAssignment).where(
                DispatcherAssignment.shift_date == shift_date,
                DispatcherAssignment.shift_num == shift_num,
                DispatcherAssignment.vehicle_id == body.vehicle_id,
                DispatcherAssignment.status == DispatcherAssignmentStatusEnum.PENDING.value,
            ),
        )
        pending_assignments: list[DispatcherAssignment] = list(pending_res.scalars().all())
        for a in pending_assignments:
            a.status = DispatcherAssignmentStatusEnum.REJECTED.value

        st_query = (
            select(ShiftTask)
            .options(selectinload(ShiftTask.route_tasks))
            .where(
                ShiftTask.shift_date == shift_date,
                ShiftTask.shift_num == shift_num,
                ShiftTask.vehicle_id == body.vehicle_id,
            )
        )
        st_res = await db.execute(st_query)
        shift_tasks_vehicle: list[ShiftTask] = list(st_res.scalars().all())

        cancelled = False
        for st in shift_tasks_vehicle:
            for rt in st.route_tasks or []:
                if rt.status == TripStatusRouteEnum.ACTIVE:
                    rt.status = TripStatusRouteEnum.REJECTED
                    cancelled = True

        await db.commit()
        if not cancelled:
            logger.debug(
                "NO_TASK move: nothing to cancel (no ACTIVE route_tasks)",
                vehicle_id=body.vehicle_id,
            )
        status_value = DispatcherAssignmentStatusEnum.APPROVED.value
        return DispatcherAssignmentResponse(
            id=0,
            vehicle_id=body.vehicle_id,
            shift_date=shift_date,
            shift_num=shift_num,
            source_kind=body.source_kind.upper(),
            source_route_place_a_id=body.source_route_place_a_id,
            source_route_place_b_id=body.source_route_place_b_id,
            source_garage_place_id=body.source_garage_place_id,
            target_kind=DispatcherAssignmentKindEnum.NO_TASK.value,
            target_route_place_a_id=None,
            target_route_place_b_id=None,
            target_garage_place_id=None,
            status=status_value,
        )

    # Если целевой тип — маршрут, проверяем, что для этой техники в текущей смене
    # уже существует route_task с нужной парой мест. Если нет — фронт должен
    # предложить создать НЗ через модалку.
    if target_kind_normalized == DispatcherAssignmentKindEnum.ROUTE.value:
        target_a = int(body.target_route_place_a_id)  # type: ignore[arg-type]
        target_b = int(body.target_route_place_b_id)  # type: ignore[arg-type]

        # 1) Проверяем "текущую" смену (как раньше).
        st_query = (
            select(ShiftTask)
            .options(selectinload(ShiftTask.route_tasks))
            .where(
                ShiftTask.shift_date == shift_date,
                ShiftTask.shift_num == shift_num,
                ShiftTask.vehicle_id == body.vehicle_id,
            )
        )
        st_res = await db.execute(st_query)
        shift_tasks_for_route: list[ShiftTask] = list(st_res.scalars().all())
        has_target_route_task = False
        revived_rejected = False
        for st in shift_tasks_for_route:
            for rt in st.route_tasks or []:
                if rt.place_a_id == target_a and rt.place_b_id == target_b:
                    # Если задача была отклонена, но мы хотим снова назначить технику на этот маршрут,
                    # "оживляем" её до DELIVERED, чтобы техника не оставалась в "Нет задания".
                    if rt.status == TripStatusRouteEnum.REJECTED:
                        rt.status = TripStatusRouteEnum.DELIVERED
                        revived_rejected = True
                    has_target_route_task = True
                    break
            if has_target_route_task:
                break

        if revived_rejected:
            await db.flush()

        if not has_target_route_task:
            logger.warning(
                "Target route_task not found in current shift",
                vehicle_id=body.vehicle_id,
                shift_date=shift_date,
                shift_num=shift_num,
                target_place_a_id=target_a,
                target_place_b_id=target_b,
            )
            raise ValueError("Target route_task for vehicle not found")

    existing_query = select(DispatcherAssignment).where(
        DispatcherAssignment.shift_date == shift_date,
        DispatcherAssignment.shift_num == shift_num,
        DispatcherAssignment.vehicle_id == body.vehicle_id,
        DispatcherAssignment.status == DispatcherAssignmentStatusEnum.PENDING.value,
    )
    existing_res = await db.execute(existing_query)
    existing: DispatcherAssignment | None = existing_res.scalars().first()

    # Если уже есть pending-назначение для этой техники в смене — считаем его
    # устаревшим и помечаем REJECTED, а новое создаём отдельной записью.
    if existing is not None:
        existing.status = DispatcherAssignmentStatusEnum.REJECTED.value
        await db.flush()

    a = DispatcherAssignment(
        vehicle_id=body.vehicle_id,
        shift_date=shift_date,
        shift_num=shift_num,
        source_kind=body.source_kind.upper(),
        source_route_place_a_id=body.source_route_place_a_id,
        source_route_place_b_id=body.source_route_place_b_id,
        source_garage_place_id=body.source_garage_place_id,
        target_kind=body.target_kind.upper(),
        target_route_place_a_id=body.target_route_place_a_id,
        target_route_place_b_id=body.target_route_place_b_id,
        target_garage_place_id=body.target_garage_place_id,
        status=DispatcherAssignmentStatusEnum.PENDING.value,
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)

    return DispatcherAssignmentResponse(
        id=a.id,
        vehicle_id=a.vehicle_id,
        shift_date=a.shift_date,
        shift_num=a.shift_num,
        source_kind=a.source_kind,
        source_route_place_a_id=a.source_route_place_a_id,
        source_route_place_b_id=a.source_route_place_b_id,
        source_garage_place_id=a.source_garage_place_id,
        target_kind=a.target_kind,
        target_route_place_a_id=a.target_route_place_a_id,
        target_route_place_b_id=a.target_route_place_b_id,
        target_garage_place_id=a.target_garage_place_id,
        status=a.status,
    )


async def decide_dispatcher_assignment(
    assignment_id: int,
    approved: bool,
    db: AsyncSession,
) -> DispatcherAssignmentResponse | None:
    """Применить решение борта по назначению (approved/rejected) и изменить route_task при необходимости."""
    # Ищем назначение только по первичному ключу, без привязки к "текущей" смене.
    # Конкретная смена берётся из самой записи назначения.
    query = (
        select(DispatcherAssignment)
        .where(DispatcherAssignment.id == assignment_id)
        .order_by(DispatcherAssignment.id.desc())
        .limit(1)
    )
    res = await db.execute(query)
    a: DispatcherAssignment | None = res.scalar_one_or_none()
    if a is None:
        return None

    # Используем смену из самой записи назначения
    shift_date: str = a.shift_date
    shift_num: int = int(a.shift_num)

    if not approved:
        a.status = DispatcherAssignmentStatusEnum.REJECTED
        await db.commit()
        await db.refresh(a)
        return DispatcherAssignmentResponse(
            id=a.id,
            vehicle_id=a.vehicle_id,
            shift_date=a.shift_date,
            shift_num=a.shift_num,
            source_kind=a.source_kind,
            source_route_place_a_id=a.source_route_place_a_id,
            source_route_place_b_id=a.source_route_place_b_id,
            source_garage_place_id=a.source_garage_place_id,
            target_kind=a.target_kind,
            target_route_place_a_id=a.target_route_place_a_id,
            target_route_place_b_id=a.target_route_place_b_id,
            target_garage_place_id=a.target_garage_place_id,
            status=a.status,
        )

    # approved: применяем
    # Загружаем все shift_tasks/route_tasks техники за эту смену один раз.
    st_query = select(ShiftTask).where(
        ShiftTask.shift_date == shift_date,
        ShiftTask.shift_num == shift_num,
        ShiftTask.vehicle_id == a.vehicle_id,
    )
    st_res = await db.execute(st_query)
    sts: list[ShiftTask] = list(st_res.scalars().all())

    # 1) Если источник — маршрут, переводим исходное НЗ:
    #    - в REJECTED при целевом гараже
    #    - в PAUSED при целевом маршруте
    if (
        a.source_kind == DispatcherAssignmentKindEnum.ROUTE
        and a.source_route_place_a_id is not None
        and a.source_route_place_b_id is not None
    ):
        for st in sts:
            for rt in st.route_tasks or []:
                if rt.status == TripStatusRouteEnum.REJECTED:
                    continue
                if rt.place_a_id == int(a.source_route_place_a_id) and rt.place_b_id == int(a.source_route_place_b_id):
                    if a.target_kind == "garage":
                        rt.status = TripStatusRouteEnum.REJECTED
                    else:
                        rt.status = TripStatusRouteEnum.PAUSED

    # 2) Если цель — маршрут (для любого source_kind),
    #    включаем целевое НЗ в ACTIVE.
    if (
        a.target_kind == DispatcherAssignmentKindEnum.ROUTE
        and a.target_route_place_a_id is not None
        and a.target_route_place_b_id is not None
    ):
        target_found = False
        for st in sts:
            for rt in st.route_tasks or []:
                if rt.status == TripStatusRouteEnum.REJECTED:
                    continue
                if rt.place_a_id == int(a.target_route_place_a_id) and rt.place_b_id == int(a.target_route_place_b_id):
                    rt.status = TripStatusRouteEnum.ACTIVE
                    target_found = True
                    break
            if target_found:
                break
        if not target_found:
            # Целевого route_task нет: трактуем как невозможность применить назначение
            # и помечаем его отклонённым, чтобы оно больше не мешало.
            a.status = DispatcherAssignmentStatusEnum.REJECTED
            await db.commit()
            await db.refresh(a)
            return DispatcherAssignmentResponse(
                id=a.id,
                vehicle_id=a.vehicle_id,
                shift_date=a.shift_date,
                shift_num=a.shift_num,
                source_kind=a.source_kind,
                source_route_place_a_id=a.source_route_place_a_id,
                source_route_place_b_id=a.source_route_place_b_id,
                source_garage_place_id=a.source_garage_place_id,
                target_kind=a.target_kind,
                target_route_place_a_id=a.target_route_place_a_id,
                target_route_place_b_id=a.target_route_place_b_id,
                target_garage_place_id=a.target_garage_place_id,
                status=a.status,
            )

    a.status = DispatcherAssignmentStatusEnum.APPROVED
    await db.commit()
    await db.refresh(a)

    return DispatcherAssignmentResponse(
        id=a.id,
        vehicle_id=a.vehicle_id,
        shift_date=a.shift_date,
        shift_num=a.shift_num,
        source_kind=a.source_kind,
        source_route_place_a_id=a.source_route_place_a_id,
        source_route_place_b_id=a.source_route_place_b_id,
        source_garage_place_id=a.source_garage_place_id,
        target_kind=a.target_kind,
        target_route_place_a_id=a.target_route_place_a_id,
        target_route_place_b_id=a.target_route_place_b_id,
        target_garage_place_id=a.target_garage_place_id,
        status=a.status,
    )


async def _calc_volume_fact_by_trips(
    db: AsyncSession,
    shift_start: datetime,
    shift_end: datetime,
) -> dict[tuple[int, int], float]:
    """Считает фактический перевезённый объём по маршрутам через рейсы за смену.

    Алгоритм:
    1. JOIN trips с place_remaining_history по cycle_id.
    2. Фильтр: place_remaining_history.timestamp в интервале [shift_start, shift_end),
               change_type = 'unloading'.
    3. GROUP BY (trips.loading_place_id, trips.unloading_place_id).
    4. SUM(ABS(change_volume)) — фактический объём unloading по маршруту.

    Один SQL-запрос, без промежуточных шагов.
    """
    if shift_start >= shift_end:
        return {}

    query = (
        select(
            Trip.loading_place_id,
            Trip.unloading_place_id,
            func.sum(func.abs(PlaceRemainingHistory.change_volume)),
        )
        .join(
            PlaceRemainingHistory,
            PlaceRemainingHistory.cycle_id == Trip.cycle_id,
        )
        .where(
            PlaceRemainingHistory.timestamp >= shift_start,
            PlaceRemainingHistory.timestamp < shift_end,
            PlaceRemainingHistory.change_type == RemainingChangeTypeEnum.unloading,
            PlaceRemainingHistory.change_volume.isnot(None),
            Trip.loading_place_id.isnot(None),
            Trip.unloading_place_id.isnot(None),
        )
        .group_by(Trip.loading_place_id, Trip.unloading_place_id)
    )

    result = await db.execute(query)

    volume_fact: dict[tuple[int, int], float] = {}
    for row in result.all():
        loading_place_id, unloading_place_id, total = row
        if total is None:
            continue
        volume_fact[(loading_place_id, unloading_place_id)] = float(total)

    return volume_fact


async def _route_exists_in_shift(
    db: AsyncSession,
    shift_date: str,
    shift_num: int,
    place_a_id: int,
    place_b_id: int,
) -> bool:
    """Проверяет, есть ли уже маршрут с такими ПП/ПР в текущей смене.

    Учитывает как шаблоны маршрутов, так и активные наряд-задания.
    """
    # 1. Проверяем шаблоны маршрутов
    tmpl_count_result = await db.execute(
        select(func.count())
        .select_from(ShiftRouteTemplate)
        .where(
            ShiftRouteTemplate.shift_date == shift_date,
            ShiftRouteTemplate.shift_num == shift_num,
            ShiftRouteTemplate.place_a_id == place_a_id,
            ShiftRouteTemplate.place_b_id == place_b_id,
        ),
    )
    tmpl_count = tmpl_count_result.scalar_one()
    if tmpl_count and tmpl_count > 0:
        return True

    # 2. Проверяем активные наряд-задания
    rt_count_result = await db.execute(
        select(func.count())
        .select_from(RouteTask)
        .join(ShiftTask, RouteTask.shift_task_id == ShiftTask.id)
        .where(
            ShiftTask.shift_date == shift_date,
            ShiftTask.shift_num == shift_num,
            RouteTask.place_a_id == place_a_id,
            RouteTask.place_b_id == place_b_id,
            RouteTask.status != TripStatusRouteEnum.REJECTED,
        ),
    )
    rt_count = rt_count_result.scalar_one()
    return bool(rt_count and rt_count > 0)


async def create_empty_route_template(
    body: RouteTemplateCreateRequest,
    db: AsyncSession,
) -> RouteTemplateResponse:
    """Создать пустой маршрут (шаблон) для текущей смены.

    Нельзя создать дубль пары (ПП, ПР), если такой маршрут уже есть в ответе
    GET /fleet-control (сводка текущей смены).
    """
    shift_info = await _get_current_shift_info()
    if not shift_info:
        logger.warning("create_empty_route_template: current shift not determined")
        return RouteTemplateResponse(
            success=False,
            message="Текущая смена не определена",
        )

    shift_date: str = shift_info["shift_date"]
    shift_num: int = shift_info["shift_num"]

    summary = await get_route_summary(db)
    for r in summary.routes:
        if r.place_a_id == body.place_a_id and r.place_b_id == body.place_b_id:
            return RouteTemplateResponse(
                success=False,
                message="Такой маршрут уже есть в текущей смене",
            )

    tmpl = ShiftRouteTemplate(
        shift_date=shift_date,
        shift_num=shift_num,
        place_a_id=body.place_a_id,
        place_b_id=body.place_b_id,
    )
    db.add(tmpl)
    await db.commit()

    return RouteTemplateResponse(
        success=True,
        message="Пустой маршрут создан",
    )


async def update_route_places(
    body: RouteTemplateUpdateRequest,
    db: AsyncSession,
) -> RouteTemplateResponse:
    """Изменить ПП/ПР существующего маршрута в текущей смене.

    Все наряд-задания маршрута в этой смене переводятся в статус REJECTED,
    а маршрут становится пустым (план/факт = 0, пока нет новых наряд-заданий).
    """
    shift_info = await _get_current_shift_info()
    if not shift_info:
        logger.warning("update_route_places: current shift not determined")
        return RouteTemplateResponse(
            success=False,
            message="Текущая смена не определена",
        )

    shift_date: str = shift_info["shift_date"]
    shift_num: int = shift_info["shift_num"]

    # Если ПП/ПР не изменились — ничего не делаем
    if body.from_place_a_id == body.to_place_a_id and body.from_place_b_id == body.to_place_b_id:
        return RouteTemplateResponse(success=True, message="Маршрут не изменён")

    # Проверяем, что нет другого маршрута с такими ПП/ПР в текущей смене
    if await _route_exists_in_shift(
        db=db,
        shift_date=shift_date,
        shift_num=shift_num,
        place_a_id=body.to_place_a_id,
        place_b_id=body.to_place_b_id,
    ):
        return RouteTemplateResponse(
            success=False,
            message="Маршрут с такими ПП и ПР уже существует в текущей смене",
        )

    # 1. Переводим все соответствующие route_tasks в статус REJECTED
    rt_result = await db.execute(
        select(RouteTask)
        .join(ShiftTask, RouteTask.shift_task_id == ShiftTask.id)
        .where(
            ShiftTask.shift_date == shift_date,
            ShiftTask.shift_num == shift_num,
            RouteTask.place_a_id == body.from_place_a_id,
            RouteTask.place_b_id == body.from_place_b_id,
            RouteTask.status != TripStatusRouteEnum.REJECTED,
        ),
    )
    route_tasks: list[RouteTask] = list(rt_result.scalars().all())

    for rt in route_tasks:
        rt.status = TripStatusRouteEnum.REJECTED

    # 2. Обновляем или создаём шаблон маршрута с новыми ПП/ПР
    tmpl_result = await db.execute(
        select(ShiftRouteTemplate).where(
            ShiftRouteTemplate.shift_date == shift_date,
            ShiftRouteTemplate.shift_num == shift_num,
            ShiftRouteTemplate.place_a_id == body.from_place_a_id,
            ShiftRouteTemplate.place_b_id == body.from_place_b_id,
        ),
    )
    tmpl: ShiftRouteTemplate | None = tmpl_result.scalar_one_or_none()

    if tmpl is None:
        tmpl = ShiftRouteTemplate(
            shift_date=shift_date,
            shift_num=shift_num,
            place_a_id=body.to_place_a_id,
            place_b_id=body.to_place_b_id,
        )
        db.add(tmpl)
    else:
        tmpl.place_a_id = body.to_place_a_id
        tmpl.place_b_id = body.to_place_b_id

    await db.commit()

    return RouteTemplateResponse(
        success=True,
        message="Маршрут обновлён, связанные наряд-задания отменены",
    )


async def delete_route_template_and_cancel_tasks(
    route_id: str,
    db: AsyncSession,
) -> RouteTemplateResponse:
    """Удалить маршрут (route template) и отменить все RouteTask для пары мест в текущей смене.

    Важно: отмена делается на бэке, потому что фронт не знает все существующие route_task.
    """
    parts = (route_id or "").split("-")
    if len(parts) != 2:
        return RouteTemplateResponse(success=False, message="Некорректный route_id (ожидается формат А-Б)")

    try:
        place_a_id = int(parts[0])
        place_b_id = int(parts[1])
    except (TypeError, ValueError):
        return RouteTemplateResponse(success=False, message="Некорректный route_id (ожидаются целые числа)")

    shift_info = await _get_current_shift_info()
    if not shift_info:
        logger.warning("delete_route: current shift not determined", route_id=route_id)
        return RouteTemplateResponse(success=False, message="Текущая смена не определена")

    shift_date: str = shift_info["shift_date"]
    shift_num: int = shift_info["shift_num"]

    # 1) Отменяем route_tasks для текущей смены и указанной пары мест.
    rt_result = await db.execute(
        select(RouteTask)
        .join(ShiftTask, RouteTask.shift_task_id == ShiftTask.id)
        .where(
            ShiftTask.shift_date == shift_date,
            ShiftTask.shift_num == shift_num,
            RouteTask.place_a_id == place_a_id,
            RouteTask.place_b_id == place_b_id,
            RouteTask.status != TripStatusRouteEnum.REJECTED,
        ),
    )
    route_tasks: list[RouteTask] = list(rt_result.scalars().all())
    for rt in route_tasks:
        rt.status = TripStatusRouteEnum.REJECTED

    # 2) Удаляем запись template (если она есть)
    tmpl_result = await db.execute(
        select(ShiftRouteTemplate).where(
            ShiftRouteTemplate.shift_date == shift_date,
            ShiftRouteTemplate.shift_num == shift_num,
            ShiftRouteTemplate.place_a_id == place_a_id,
            ShiftRouteTemplate.place_b_id == place_b_id,
        ),
    )
    tmpl = tmpl_result.scalar_one_or_none()
    template_deleted = tmpl is not None
    if tmpl is not None:
        await db.delete(tmpl)

    await db.commit()

    return RouteTemplateResponse(
        success=True,
        message=(
            f"Маршрут {route_id} удалён; отменено наряд-заданий: {len(route_tasks)}"
            + ("; template удалён" if template_deleted else "")
        ),
    )
