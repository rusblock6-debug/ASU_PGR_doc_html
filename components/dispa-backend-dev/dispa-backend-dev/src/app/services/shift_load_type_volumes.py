"""Объёмы по видам груза за текущую смену из place_remaining_history + trips."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.shift_load_type_volumes import ShiftLoadTypeVolumeRow, ShiftLoadTypeVolumesResponse
from app.database.models import PlaceRemainingHistory, Trip
from app.enums import RemainingChangeTypeEnum
from app.services.place_info import get_load_type, get_place
from app.services.route_summary import (
    _get_cached_shift_time_range,
    _get_current_shift_info,
    _get_section_ids_for_place,
)


def _load_type_display_name(info: dict[str, Any] | None) -> str:
    if not info:
        return ""
    for key in ("name", "title", "system_name"):
        raw = info.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return ""


async def _cargo_type_for_loading_place(place_id: int) -> tuple[int, int | None]:
    pinfo = await get_place(place_id)
    if not pinfo:
        return place_id, None
    raw_ct = pinfo.get("cargo_type")
    if raw_ct is None:
        return place_id, None
    try:
        return place_id, int(raw_ct)
    except (TypeError, ValueError):
        logger.debug("shift_load_type_volumes: bad cargo_type", place_id=place_id, cargo_type=raw_ct)
        return place_id, None


def _empty_response(
    *,
    shift_date: str = "",
    shift_num: int = 0,
) -> ShiftLoadTypeVolumesResponse:
    return ShiftLoadTypeVolumesResponse(
        shift_date=shift_date,
        shift_num=shift_num,
        items=[],
    )


async def get_shift_load_type_volumes(
    db: AsyncSession,
    *,
    section_ids: tuple[int, ...] | None = None,
    place_ids: tuple[int, ...] | None = None,
) -> ShiftLoadTypeVolumesResponse:
    """Собрать объёмы разгрузки за текущую смену, сгруппированные по виду груза.

    Источник объёма: place_remaining_history (unloading) за интервал смены, JOIN trips по cycle_id.
    Вид груза: cargo_type места погрузки (loading_place_id), как при расчёте change_amount.
    Участок места разгрузки: horizon graph-service → section_id.

    volume_sections_m3: при переданных section_ids — разгрузки на любом из участков (OR); иначе полная сумма по смене.
    volume_places_m3: при переданных place_ids — любое из указанных мест разгрузки (OR); иначе полная сумма по смене.
    Без фильтров оба значения в строке совпадают.
    """
    section_filter = frozenset(section_ids) if section_ids else None
    place_filter = frozenset(place_ids) if place_ids else None

    shift_info = await _get_current_shift_info()
    if not shift_info:
        logger.warning("shift_load_type_volumes: current shift not determined")
        return _empty_response()

    shift_date = str(shift_info.get("shift_date") or "")
    shift_num_raw = shift_info.get("shift_num")
    shift_num = int(shift_num_raw) if shift_num_raw is not None else 0

    shift_range = await _get_cached_shift_time_range(shift_date=shift_date, shift_num=shift_num)
    if not shift_range:
        logger.warning(
            "shift_load_type_volumes: shift time range missing",
            shift_date=shift_date,
            shift_num=shift_num,
        )
        return _empty_response(shift_date=shift_date, shift_num=shift_num)

    shift_start = shift_range["start_time"]
    shift_end = shift_range["end_time"]
    if shift_start >= shift_end:
        return _empty_response(shift_date=shift_date, shift_num=shift_num)

    query = (
        select(
            Trip.loading_place_id,
            PlaceRemainingHistory.place_id.label("unloading_place_id"),
            func.sum(func.abs(PlaceRemainingHistory.change_amount)),
        )
        .join(PlaceRemainingHistory, PlaceRemainingHistory.cycle_id == Trip.cycle_id)
        .where(
            PlaceRemainingHistory.timestamp >= shift_start,
            PlaceRemainingHistory.timestamp < shift_end,
            PlaceRemainingHistory.change_type == RemainingChangeTypeEnum.unloading,
            Trip.loading_place_id.isnot(None),
            PlaceRemainingHistory.cycle_id.isnot(None),
        )
        .group_by(Trip.loading_place_id, PlaceRemainingHistory.place_id)
    )

    result = await db.execute(query)
    grouped_rows: list[tuple[int, int, float]] = []
    for loading_pid, unloading_pid, total in result.all():
        grouped_rows.append((int(loading_pid), int(unloading_pid), float(total)))

    unique_loading = {r[0] for r in grouped_rows}
    unique_unloading = {r[1] for r in grouped_rows}

    cargo_pairs = await asyncio.gather(*[_cargo_type_for_loading_place(pid) for pid in unique_loading])
    loading_to_cargo = dict(cargo_pairs)

    section_pairs = await asyncio.gather(*[_get_section_ids_for_place(pid) for pid in unique_unloading])
    unloading_to_section_ids = dict(zip(unique_unloading, section_pairs, strict=True))

    totals_full: dict[int, float] = defaultdict(float)
    totals_section_slice: dict[int, float] = defaultdict(float)
    totals_place_slice: dict[int, float] = defaultdict(float)

    for loading_pid, unloading_pid, vol in grouped_rows:
        lt_id = loading_to_cargo.get(loading_pid)
        if lt_id is None:
            continue

        totals_full[lt_id] += vol

        if section_filter is None:
            totals_section_slice[lt_id] += vol
        else:
            sec_ids = unloading_to_section_ids.get(unloading_pid, [])
            if any(sec in section_filter for sec in sec_ids):
                totals_section_slice[lt_id] += vol

        # volume_places_m3:
        # - если place_ids не переданы, но section_ids переданы — фильтруем по section_ids
        # - если place_ids переданы — фильтруем по месту (и дополнительно по section_ids, если они переданы)
        if place_filter is None:
            if section_filter is None:
                totals_place_slice[lt_id] += vol
            else:
                sec_ids = unloading_to_section_ids.get(unloading_pid, [])
                if any(sec in section_filter for sec in sec_ids):
                    totals_place_slice[lt_id] += vol
        else:
            if unloading_pid not in place_filter:
                continue
            if section_filter is not None:
                sec_ids = unloading_to_section_ids.get(unloading_pid, [])
                if not any(sec in section_filter for sec in sec_ids):
                    continue
            totals_place_slice[lt_id] += vol

    all_type_ids = sorted(totals_full.keys())
    lt_infos = await asyncio.gather(*[get_load_type(lt_id) for lt_id in all_type_ids])
    rows = [
        ShiftLoadTypeVolumeRow(
            load_type_id=lt_id,
            load_type_name=_load_type_display_name(lt_info),
            volume_sections_m3=totals_section_slice.get(lt_id, 0.0),
            volume_places_m3=totals_place_slice.get(lt_id, 0.0),
        )
        for lt_id, lt_info in zip(all_type_ids, lt_infos, strict=True)
    ]

    rows.sort(key=lambda r: (r.load_type_name.casefold(), r.load_type_id))

    return ShiftLoadTypeVolumesResponse(
        shift_date=shift_date,
        shift_num=shift_num,
        items=rows,
    )
