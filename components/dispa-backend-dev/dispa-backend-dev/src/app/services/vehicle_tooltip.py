"""Сервис для формирования тултипа по технике на карте."""

from __future__ import annotations

import ast
import asyncio
import json
import time
from datetime import UTC, datetime
from typing import Any

import httpx
from loguru import logger
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.vehicle_tooltip import VehicleTooltipResponse
from app.core.config import settings
from app.core.redis_client import redis_client
from app.database.models import Cycle, CycleStateHistory, RouteTask, ShiftTask
from app.enums.route_tasks import TripStatusRouteEnum
from app.services.place_info import get_place

_SHIFT_INFO_CACHE_TTL_S = 5.0
_shift_info_cache: tuple[float, dict[str, Any] | None] | None = None

_place_name_cache: dict[int, tuple[float, str | None]] = {}
_PLACE_NAME_CACHE_TTL_S = 60.0

_TELEMETRY_GPS_PREFIX = "telemetry-service:gps:"
_TELEMETRY_SPEED_PREFIX = "telemetry-service:speed:"
_TELEMETRY_WEIGHT_PREFIX = "telemetry-service:weight:"


def _telemetry_stream_key(prefix: str, vehicle_id: int) -> str:
    return f"{prefix}{vehicle_id}"


def _parse_stream_value(raw_data: Any) -> float | None:
    """Извлечь float из стрим-сообщения telemetry-service.

    Ожидаемый формат:
      {"metadata": {...}, "data": {"value": 18, ...}}
    """
    if raw_data is None:
        return None

    try:
        if isinstance(raw_data, (bytes, bytearray)):
            s = raw_data.decode("utf-8")
        else:
            s = str(raw_data)

        try:
            obj = json.loads(s)
        except (ValueError, TypeError):
            obj = ast.literal_eval(s)

        if not isinstance(obj, dict):
            return None

        inner = obj.get("data")
        if not isinstance(inner, dict):
            return None

        val = inner.get("value")
        if val is None:
            return None
        return float(val)
    except Exception:
        return None


def _parse_stream_timestamp_field(raw_ts: Any) -> float | None:
    """Поле timestamp в записи Stream (unix seconds, строка), см. telemetry_storage.store_telemetry."""
    if raw_ts is None:
        return None
    try:
        if isinstance(raw_ts, (bytes, bytearray)):
            raw_ts = raw_ts.decode("utf-8")
        return float(raw_ts)
    except (ValueError, TypeError):
        return None


def _format_utc_z(dt: datetime) -> str:
    """UTC с суффиксом Z, точность до секунд (без дробной части)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


async def _read_last_stream_row(prefix: str, vehicle_id: int) -> tuple[float | None, float | None]:
    """Последняя запись Stream: (metric value из JSON data, unix time из поля timestamp)."""
    if redis_client.redis is None:
        return None, None

    key = _telemetry_stream_key(prefix=prefix, vehicle_id=vehicle_id)
    try:
        entries: list[tuple[Any, dict[Any, Any]]] = await redis_client.redis.xrevrange(
            key,
            max="+",
            min="-",
            count=1,
        )
    except Exception as e:
        logger.debug("Telemetry stream read failed", key=key, error=str(e))
        return None, None

    if not entries:
        return None, None

    _entry_id, data = entries[0]
    if not data:
        return None, None

    raw_data = data.get("data") or data.get(b"data")
    raw_ts = data.get("timestamp") or data.get(b"timestamp")
    return _parse_stream_value(raw_data), _parse_stream_timestamp_field(raw_ts)


async def _get_current_shift_info_cached() -> dict[str, Any] | None:
    global _shift_info_cache
    now_m = time.monotonic()
    if _shift_info_cache is not None:
        cached_at, cached = _shift_info_cache
        if now_m - cached_at < _SHIFT_INFO_CACHE_TTL_S:
            return cached

    # Enterprise-service expects a timestamp parameter; route_summary использует tz-naive isoformat.
    now_utc = datetime.now(UTC).replace(tzinfo=None)
    url = f"{settings.enterprise_service_url}/api/shift-service/get-shift-info-by-timestamp"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, params={"timestamp": now_utc.isoformat()})
            if resp.status_code == 200:
                payload = resp.json()
                _shift_info_cache = (now_m, payload)
                return payload
    except Exception as e:
        logger.debug("Failed to get current shift info", error=str(e))

    _shift_info_cache = (now_m, None)
    return None


async def _get_place_name_optional_cached(place_id: int) -> str | None:
    """Имя места из graph-service или null (без синтетических '-' / '#id')."""
    now_m = time.monotonic()
    cached = _place_name_cache.get(place_id)
    if cached is not None:
        cached_at, cached_name = cached
        if now_m - cached_at < _PLACE_NAME_CACHE_TTL_S:
            return cached_name

    place_info = await get_place(place_id)
    name: str | None = None
    if place_info and isinstance(place_info, dict):
        raw = place_info.get("name")
        if raw is not None and str(raw).strip():
            name = str(raw).strip()

    _place_name_cache[place_id] = (now_m, name)
    return name


async def get_vehicle_tooltip(
    vehicle_id: int,
    db: AsyncSession,
) -> VehicleTooltipResponse:
    """Собрать данные, необходимые для тултипа на карте."""
    now_utc = datetime.now(UTC).replace(tzinfo=None)
    last_history: CycleStateHistory | None = None

    try:
        query = (
            select(CycleStateHistory)
            .where(CycleStateHistory.vehicle_id == vehicle_id)
            .order_by(desc(CycleStateHistory.timestamp))
            .limit(1)
        )
        history_result = await db.execute(query)
        last_history = history_result.scalar_one_or_none()
    except Exception as e:
        logger.debug("Failed to fetch last cycle_state_history", vehicle_id=vehicle_id, error=str(e))

    resolved_state: str | None = None
    state_duration: int | None = None
    last_place_id: int | None = None

    if last_history is not None:
        last_place_id = last_history.place_id
        hist_state = last_history.state
        if hist_state is not None and str(hist_state).strip():
            resolved_state = str(hist_state).strip()
            try:
                duration_s = (now_utc - last_history.timestamp.replace(tzinfo=None)).total_seconds()
                state_duration = max(0, int(duration_s))
            except Exception:
                state_duration = None

    try:
        state_data = await redis_client.get_state_machine_data(str(vehicle_id))
        if isinstance(state_data, dict):
            redis_last_place_id = state_data.get("last_place_id")
            if redis_last_place_id is not None:
                last_place_id = int(redis_last_place_id)
            if resolved_state is None and state_data.get("state") is not None:
                rs = str(state_data.get("state")).strip()
                if rs:
                    resolved_state = rs
    except Exception as e:
        logger.debug("Failed to read state machine data", vehicle_id=vehicle_id, error=str(e))

    state = resolved_state if resolved_state is not None else "no_data"

    place_name: str | None = None
    if last_place_id is not None:
        try:
            place_name = await _get_place_name_optional_cached(last_place_id)
        except Exception as e:
            logger.debug("Failed to resolve place_name", vehicle_id=vehicle_id, place_id=last_place_id, error=str(e))

    (w_val, w_ts), (s_val, s_ts), (_g_val, g_ts) = await asyncio.gather(
        _read_last_stream_row(_TELEMETRY_WEIGHT_PREFIX, vehicle_id),
        _read_last_stream_row(_TELEMETRY_SPEED_PREFIX, vehicle_id),
        _read_last_stream_row(_TELEMETRY_GPS_PREFIX, vehicle_id),
    )
    weight = w_val
    speed = s_val

    ts_candidates = [t for t in (g_ts, s_ts, w_ts) if t is not None]
    if ts_candidates:
        last_message_timestamp = _format_utc_z(datetime.fromtimestamp(max(ts_candidates), tz=UTC))
    else:
        last_message_timestamp = None

    planned_trips_count: int | None = None
    actual_trips_count: int | None = None

    shift_info = await _get_current_shift_info_cached()
    if shift_info:
        try:
            shift_date = str(shift_info.get("shift_date"))
            shift_num_raw = shift_info.get("shift_num")
            shift_num = int(shift_num_raw) if shift_num_raw is not None else 0

            last_active_task_query = (
                select(RouteTask)
                .join(ShiftTask, RouteTask.shift_task_id == ShiftTask.id)
                .where(ShiftTask.shift_date == shift_date)
                .where(ShiftTask.shift_num == shift_num)
                .where(ShiftTask.vehicle_id == vehicle_id)
                .where(RouteTask.status == TripStatusRouteEnum.ACTIVE)
                .order_by(desc(RouteTask.created_at), desc(RouteTask.id))
                .limit(1)
            )
            active_result = await db.execute(last_active_task_query)
            last_active_task: RouteTask | None = active_result.scalar_one_or_none()

            if last_active_task is not None:
                planned_trips_count = int(last_active_task.planned_trips_count or 0)
                completed_cycles_query = (
                    select(func.count())
                    .select_from(Cycle)
                    .where(
                        Cycle.vehicle_id == vehicle_id,
                        Cycle.task_id == str(last_active_task.id),
                        Cycle.cycle_completed_at.is_not(None),
                    )
                )
                completed_cycles_result = await db.execute(completed_cycles_query)
                actual_trips_count = int(completed_cycles_result.scalar() or 0)
        except Exception as e:
            logger.debug("Failed to calculate trips counts", vehicle_id=vehicle_id, error=str(e))

    return VehicleTooltipResponse(
        state=state,
        state_duration=state_duration,
        actual_trips_count=actual_trips_count,
        planned_trips_count=planned_trips_count,
        weight=weight,
        speed=speed,
        place_name=place_name,
        last_message_timestamp=last_message_timestamp,
    )
