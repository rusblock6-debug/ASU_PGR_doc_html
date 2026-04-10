"""API endpoints для журнала событий.

Предоставляет доступ к истории состояний и меток.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

import httpx
from auth_lib.dependencies import require_permission
from auth_lib.permissions import Action, Permission
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import String, and_, desc, func, or_, select
from sqlalchemy import cast as sa_cast
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.event_log import (
    CurrentShiftStatsResponse,
    CycleStateHistoryResponse,
    CycleTagHistoryResponse,
    EventLogListResponse,
    FullShiftStateHistoryResponse,
)
from app.core.config import settings
from app.database.models import (
    CycleStateHistory,
    CycleTagHistory,
    FullShiftStateHistory,
    PlaceRemainingHistory,
    RouteTask,
    ShiftTask,
    Trip,
)
from app.services.enterprise_client import enterprise_client
from app.utils.session import SessionDepends

router = APIRouter(prefix="/event-log", tags=["event-log"])


@router.get(
    "/state-history",
    response_model=EventLogListResponse,
    dependencies=[Depends(require_permission((Permission.WORK_TIME_MAP, Action.VIEW)))],
)
async def get_state_history(
    session: SessionDepends,
    from_date: date = Query(
        ...,
        description="Дата начала интервала включительно (YYYY-MM-DD)",
    ),
    to_date: date = Query(
        ...,
        description="Дата окончания интервала включительно (YYYY-MM-DD)",
    ),
    from_shift_num: int = Query(
        ...,
        ge=1,
        description="Номер смены начала включительно (1, 2, etc.)",
    ),
    to_shift_num: int = Query(
        ...,
        ge=1,
        description="Номер смены окончания включительно (1, 2, etc.)",
    ),
    vehicle_ids: list[int] | None = Query(
        None,
        description="Список ID транспортных средств для фильтрации. Если пустой или не указан - без фильтрации",
    ),
    is_full_shift: bool = Query(
        False,
        description="Если true — возвращать обобщённые полносменные статусы из full_shift_state_history",
    ),
    page: int | None = Query(None, ge=1, description="Номер страницы"),
    size: int | None = Query(None, ge=1, le=10000, description="Размер страницы"),
) -> EventLogListResponse:
    """Получить историю состояний State Machine с фильтрацией по сменам.

    Интервалы включительные. В каждом дне 2 смены.

    from_shift_num и to_shift_num задают границы непрерывного интервала:
    «с N-й смены from_date по M-ю смену to_date» — включаются ВСЕ смены внутри.

    Пример: from_date=31, to_date=2, from_shift_num=1, to_shift_num=1 →
    31-е: смена 1 и 2, 1-е: смена 1 и 2, 2-е: смена 1.

    При is_full_shift=true возвращаются обобщённые записи из full_shift_state_history.
    """
    SHIFTS_PER_DAY = 2

    if to_date < from_date:
        raise HTTPException(
            status_code=400,
            detail="to_date должен быть >= from_date (интервал дат включительный).",
        )

    logger.info(
        "State history request",
        from_date=from_date.isoformat(),
        to_date=to_date.isoformat(),
        from_shift_num=from_shift_num,
        to_shift_num=to_shift_num,
        is_full_shift=is_full_shift,
    )

    if is_full_shift:
        return await _get_aggregated_state_history(
            from_date=from_date,
            to_date=to_date,
            from_shift_num=from_shift_num,
            to_shift_num=to_shift_num,
            shifts_per_day=SHIFTS_PER_DAY,
            vehicle_ids=vehicle_ids,
            page=page,
            size=size,
            db=session,
        )

    # Иначе возвращаем детальные данные из cycle_state_history
    return await _get_detailed_state_history(
        from_date=from_date,
        to_date=to_date,
        from_shift_num=from_shift_num,
        to_shift_num=to_shift_num,
        shifts_per_day=SHIFTS_PER_DAY,
        vehicle_ids=vehicle_ids,
        page=page,
        size=size,
        db=session,
    )


async def _get_aggregated_state_history(
    from_date: date,
    to_date: date,
    from_shift_num: int,
    to_shift_num: int,
    shifts_per_day: int,
    vehicle_ids: list[int] | None,
    page: int | None,
    size: int | None,
    db: AsyncSession,
) -> EventLogListResponse:
    """Получить обобщенные данные из full_shift_state_history."""

    def shift_range_for_day(d: date) -> range:
        if from_date == to_date:
            return range(from_shift_num, to_shift_num + 1)
        if d == from_date:
            return range(from_shift_num, shifts_per_day + 1)
        if d == to_date:
            return range(1, to_shift_num + 1)
        return range(1, shifts_per_day + 1)

    # Собираем условия для каждой смены в диапазоне
    shift_conditions = []
    current_date = from_date
    while current_date <= to_date:
        for shift_num in shift_range_for_day(current_date):
            shift_conditions.append(
                and_(
                    FullShiftStateHistory.shift_date == current_date.isoformat(),
                    FullShiftStateHistory.shift_num == shift_num,
                ),
            )
        current_date += timedelta(days=1)

    conditions = [or_(*shift_conditions)]

    if vehicle_ids:
        conditions.append(FullShiftStateHistory.vehicle_id.in_(vehicle_ids))

    # Запрос
    query = select(FullShiftStateHistory).where(and_(*conditions)).order_by(desc(FullShiftStateHistory.timestamp))

    # Подсчет
    count_query = select(func.count()).select_from(
        select(FullShiftStateHistory.id).where(and_(*conditions)).subquery(),
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    use_pagination = page is not None or size is not None

    if use_pagination:
        page = page if page is not None else 1
        size = size if size is not None else 20
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)

        result = await db.execute(query)
        items = result.scalars().all()
        pages = (total + size - 1) // size if total > 0 else 1

        return EventLogListResponse(
            items=[FullShiftStateHistoryResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
    else:
        result = await db.execute(query)
        items = result.scalars().all()

        return EventLogListResponse(
            items=[FullShiftStateHistoryResponse.model_validate(item) for item in items],
            total=total,
            page=1,
            size=total,
            pages=1,
        )


async def _get_detailed_state_history(
    from_date: date,
    to_date: date,
    from_shift_num: int,
    to_shift_num: int,
    shifts_per_day: int,
    vehicle_ids: list[int] | None,
    page: int | None,
    size: int | None,
    db: AsyncSession,
) -> EventLogListResponse:
    """Получить детальные данные из cycle_state_history."""
    conditions = []
    shift_time_conditions = []
    failed_ranges: list[str] = []

    def shift_range_for_day(d: date) -> range:
        if from_date == to_date:
            return range(from_shift_num, to_shift_num + 1)
        if d == from_date:
            return range(from_shift_num, shifts_per_day + 1)
        if d == to_date:
            return range(1, to_shift_num + 1)
        return range(1, shifts_per_day + 1)

    current_date = from_date
    while current_date <= to_date:
        for shift_num in shift_range_for_day(current_date):
            ok = False
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{settings.enterprise_service_url}/api/shift-service/get-shift-time-range",
                        params={
                            "shift_date": current_date.isoformat(),
                            "shift_number": shift_num,
                        },
                        timeout=5.0,
                    )

                    if response.status_code == 200:
                        shift_data = response.json()
                        if shift_data and "start_time" in shift_data and "end_time" in shift_data:
                            start_time = datetime.fromisoformat(shift_data["start_time"])
                            end_time = datetime.fromisoformat(shift_data["end_time"])

                            start_time_utc = start_time.astimezone(UTC)
                            end_time_utc = end_time.astimezone(UTC)

                            shift_time_conditions.append(
                                and_(
                                    CycleStateHistory.timestamp >= start_time_utc,
                                    CycleStateHistory.timestamp <= end_time_utc,
                                ),
                            )
                            ok = True
                    if not ok:
                        failed_ranges.append(f"{current_date.isoformat()} смена {shift_num}")
            except Exception as e:
                logger.error(
                    "Failed to get shift time range from enterprise-service",
                    shift_date=current_date.isoformat(),
                    shift_number=shift_num,
                    error=str(e),
                )
                failed_ranges.append(f"{current_date.isoformat()} смена {shift_num}")

        current_date += timedelta(days=1)

    if failed_ranges:
        raise HTTPException(
            status_code=400,
            detail=(
                "Не удалось получить временные интервалы для части смен: "
                + ", ".join(failed_ranges)
                + ". Проверьте параметры и доступность enterprise-service."
            ),
        )
    if not shift_time_conditions:
        raise HTTPException(
            status_code=400,
            detail="Не удалось получить временные интервалы для указанных смен. "
            "Проверьте корректность параметров from_shift_num и to_shift_num.",
        )

    conditions.append(or_(*shift_time_conditions))

    if vehicle_ids:
        logger.debug("Applying vehicle_ids filter", vehicle_ids=vehicle_ids)
        conditions.append(CycleStateHistory.vehicle_id.in_(vehicle_ids))
    else:
        logger.debug("No vehicle_ids filter applied")

    query = select(CycleStateHistory).where(and_(*conditions)).order_by(desc(CycleStateHistory.timestamp))

    count_query = select(func.count()).select_from(
        select(CycleStateHistory.id).where(and_(*conditions)).subquery(),
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    use_pagination = page is not None or size is not None

    if use_pagination:
        page = page if page is not None else 1
        size = size if size is not None else 20

        offset = (page - 1) * size
        query = query.offset(offset).limit(size)

        result = await db.execute(query)
        items = result.scalars().all()

        pages = (total + size - 1) // size if total > 0 else 1

        return EventLogListResponse(
            items=[CycleStateHistoryResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
    else:
        result = await db.execute(query)
        items = result.scalars().all()

        return EventLogListResponse(
            items=[CycleStateHistoryResponse.model_validate(item) for item in items],
            total=total,
            page=1,
            size=total,
            pages=1,
        )


@router.get(
    "/tag-history",
    response_model=EventLogListResponse,
)
async def get_tag_history(
    session: SessionDepends,
    period: Literal["hour", "shift", "day", "month"] = Query(
        "hour",
        description="Период: hour, shift, day, month",
    ),
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(20, ge=1, le=100, description="Размер страницы"),
) -> EventLogListResponse:
    """Получить историю меток локации.

    Фильтрация по периоду:
    - hour: последний час
    - shift: последняя смена (8 часов)
    - day: последний день (24 часа)
    - month: последний месяц (30 дней)
    """
    # Определяем временной диапазон
    now = datetime.now(UTC)
    period_map = {
        "hour": timedelta(hours=1),
        "shift": timedelta(hours=8),
        "day": timedelta(days=1),
        "month": timedelta(days=30),
    }
    time_from = now - period_map[period]

    # Запрос с фильтрацией по времени
    query = (
        select(CycleTagHistory).where(CycleTagHistory.timestamp >= time_from).order_by(desc(CycleTagHistory.timestamp))
    )

    # Подсчет общего количества
    count_query = select(func.count()).select_from(
        select(CycleTagHistory.id).where(CycleTagHistory.timestamp >= time_from).subquery(),
    )
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Пагинация
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    # Выполнение запроса
    result = await session.execute(query)
    items = result.scalars().all()

    # Формирование ответа
    pages = (total + size - 1) // size if total > 0 else 1

    return EventLogListResponse(
        items=[CycleTagHistoryResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get(
    "/current-shift-stats",
    response_model=CurrentShiftStatsResponse,
    dependencies=[Depends(require_permission((Permission.WORK_TIME_MAP, Action.VIEW)))],
)
async def get_current_shift_stats(
    session: SessionDepends,
    vehicle_id: int | None = Query(None, description="Фильтр по ID транспортного средства"),
) -> CurrentShiftStatsResponse:
    """Получить агрегированную статистику по текущей смене."""
    shift_data = await enterprise_client.get_shift_info_and_time_range(timestamp=datetime.now(UTC))
    if not shift_data:
        raise HTTPException(
            status_code=400,
            detail="Не удалось определить текущую смену через enterprise-service",
        )

    shift_date_raw = shift_data.get("shift_date")
    shift_num_raw = shift_data.get("shift_num")
    shift_start_raw = shift_data.get("start_time")
    shift_end_raw = shift_data.get("end_time")

    if not isinstance(shift_date_raw, date):
        raise HTTPException(status_code=400, detail="Некорректный формат shift_date от enterprise-service")
    if not isinstance(shift_num_raw, int):
        raise HTTPException(status_code=400, detail="Некорректный формат shift_num от enterprise-service")
    if not isinstance(shift_start_raw, datetime) or not isinstance(shift_end_raw, datetime):
        raise HTTPException(status_code=400, detail="Некорректный формат диапазона смены от enterprise-service")

    shift_date: date = shift_date_raw
    shift_num: int = shift_num_raw
    shift_start: datetime = shift_start_raw
    shift_end: datetime = shift_end_raw
    effective_end = shift_end

    if shift_end <= shift_start:
        return CurrentShiftStatsResponse(
            shift_date=shift_date.isoformat(),
            shift_num=shift_num,
            work_time_sum=0,
            idle_time_sum=0,
            actual_trips_count_sum=0,
            planned_trips_count_sum=0,
            actual_weight_sum=0,
            planned_weight_sum=0,
        )

    try:
        statuses = await enterprise_client.get_all_statuses()
    except Exception as exc:
        logger.warning("Failed to fetch statuses for current shift stats", error=str(exc))
        statuses = []
    status_work_map: dict[str, bool] = {
        str(item.get("system_name")): bool(item.get("is_work_status", False))
        for item in statuses
        if item.get("system_name")
    }

    state_conditions = [
        CycleStateHistory.timestamp >= shift_start,
        CycleStateHistory.timestamp < effective_end,
    ]
    if vehicle_id is not None:
        state_conditions.append(sa_cast(CycleStateHistory.vehicle_id, String) == str(vehicle_id))

    in_shift_query = (
        select(CycleStateHistory)
        .where(*state_conditions)
        .order_by(
            CycleStateHistory.vehicle_id,
            CycleStateHistory.timestamp,
        )
    )
    in_shift_result = await session.execute(in_shift_query)
    in_shift_records = list(in_shift_result.scalars().all())

    vehicle_ids = sorted({record.vehicle_id for record in in_shift_records})
    prev_records_by_vehicle: dict[int, CycleStateHistory] = {}
    if vehicle_ids:
        prev_ts_subq = (
            select(
                CycleStateHistory.vehicle_id.label("vehicle_id"),
                func.max(CycleStateHistory.timestamp).label("max_ts"),
            )
            .where(
                CycleStateHistory.vehicle_id.in_(vehicle_ids),
                CycleStateHistory.timestamp < shift_start,
            )
            .group_by(CycleStateHistory.vehicle_id)
            .subquery()
        )
        prev_query = select(CycleStateHistory).join(
            prev_ts_subq,
            (CycleStateHistory.vehicle_id == prev_ts_subq.c.vehicle_id)
            & (CycleStateHistory.timestamp == prev_ts_subq.c.max_ts),
        )
        prev_result = await session.execute(prev_query)
        for prev_record in prev_result.scalars().all():
            prev_records_by_vehicle[prev_record.vehicle_id] = prev_record

    records_by_vehicle: dict[int, list[CycleStateHistory]] = {}
    for record in in_shift_records:
        records_by_vehicle.setdefault(record.vehicle_id, []).append(record)

    work_seconds = 0.0
    idle_seconds = 0.0

    for current_vehicle_id, records in records_by_vehicle.items():
        timeline = []
        previous_record: CycleStateHistory | None = prev_records_by_vehicle.get(current_vehicle_id)
        if previous_record is not None:
            timeline.append(previous_record)
        timeline.extend(records)
        timeline.sort(key=lambda item: item.timestamp)

        for idx, current in enumerate(timeline):
            if current.state not in status_work_map:
                continue
            seg_start = max(current.timestamp, shift_start)
            seg_end = effective_end
            if idx + 1 < len(timeline):
                seg_end = min(timeline[idx + 1].timestamp, effective_end)

            duration = float((seg_end - seg_start).total_seconds())
            if duration <= 0:
                continue

            if status_work_map[current.state]:
                work_seconds += duration
            else:
                idle_seconds += duration

    trip_conditions = [
        Trip.end_time.is_not(None),
        Trip.end_time >= shift_start,
        Trip.end_time < effective_end,
    ]
    if vehicle_id is not None:
        trip_conditions.append(sa_cast(Trip.vehicle_id, String) == str(vehicle_id))

    actual_trips_count_query = select(func.count(Trip.cycle_id)).where(*trip_conditions)
    actual_trips_count_sum = int((await session.execute(actual_trips_count_query)).scalar_one() or 0)

    planned_conditions: list[Any] = [
        ShiftTask.shift_date == shift_date.isoformat(),
        ShiftTask.shift_num == shift_num,
    ]
    if vehicle_id is not None:
        planned_conditions.append(sa_cast(ShiftTask.vehicle_id, String) == str(vehicle_id))

    planned_query = select(
        func.coalesce(func.sum(RouteTask.planned_trips_count), 0),
        func.coalesce(func.sum(RouteTask.weight), 0.0),
    ).join(ShiftTask, RouteTask.shift_task_id == ShiftTask.id)
    for condition in planned_conditions:
        planned_query = planned_query.where(condition)
    planned_result = await session.execute(planned_query)
    planned_trips_count_raw, planned_weight_raw = planned_result.one()

    weight_conditions = [
        PlaceRemainingHistory.timestamp >= shift_start,
        PlaceRemainingHistory.timestamp < effective_end,
        PlaceRemainingHistory.change_amount > 0,
    ]
    if vehicle_id is not None:
        weight_conditions.append(
            func.coalesce(
                sa_cast(PlaceRemainingHistory.vehicle_id, String),
                sa_cast(Trip.vehicle_id, String),
            )
            == str(vehicle_id),
        )

    # Фактический объем считаем строго по timestamp-интервалу смены, без привязки к shift_id.
    actual_weight_query = (
        select(func.coalesce(func.sum(PlaceRemainingHistory.change_amount), 0.0))
        .select_from(PlaceRemainingHistory)
        .outerjoin(Trip, Trip.cycle_id == PlaceRemainingHistory.cycle_id)
        .where(*weight_conditions)
    )
    actual_weight_raw = (await session.execute(actual_weight_query)).scalar_one()

    return CurrentShiftStatsResponse(
        shift_date=shift_date.isoformat(),
        shift_num=shift_num,
        work_time_sum=int(round(work_seconds / 60)),
        idle_time_sum=int(round(idle_seconds / 60)),
        actual_trips_count_sum=actual_trips_count_sum,
        planned_trips_count_sum=int(planned_trips_count_raw or 0),
        actual_weight_sum=int(round(float(actual_weight_raw or 0.0))),
        planned_weight_sum=int(round(float(planned_weight_raw or 0.0))),
    )
