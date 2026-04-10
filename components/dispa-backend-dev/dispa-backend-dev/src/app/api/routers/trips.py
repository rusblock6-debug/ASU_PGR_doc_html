"""API endpoints для trips и истории."""

import asyncio
import time
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from zoneinfo import ZoneInfo

import httpx
from auth_lib.dependencies import require_permission
from auth_lib.permissions import Action, Permission
from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import CursorResult, delete, desc, func, select

from app.api.schemas.common import PaginatedResponse
from app.api.schemas.history import PlaceRemainingHistoryCreate
from app.api.schemas.trips import (
    CycleAnalyticsResponse,
    CycleStateHistoryResponse,
    CycleTagHistoryResponse,
    TripCreate,
    TripResponse,
    TripUpdate,
)
from app.core.config import settings
from app.core.redis_client import redis_client
from app.database.base import generate_uuid
from app.database.models import (
    Cycle,
    CycleAnalytics,
    CycleStateHistory,
    CycleTagHistory,
    Trip,
)
from app.enums import RemainingChangeTypeEnum
from app.services.full_shift_state_service import full_shift_state_service
from app.services.place_remaining import place_remaining_service
from app.services.state_history_service import (
    _publish_history_changed_event,
    get_shift_info_for_timestamp,
    get_status_display_name,
)
from app.services.trip_manager import bulk_update_trips_cycle_num, get_place_remaining_history_by_trips
from app.services.trip_state_sync_service import (
    check_trip_overlap,
    create_no_data_status_after_cycle_deletion,
    create_trip_state_history,
    delete_trip_state_history,
    publish_trip_history_changed_event,
    update_trip_state_history,
)
from app.utils.datetime_utils import format_time_for_message, truncate_datetime_to_seconds
from app.utils.session import SessionDepends

# Кэш названий мест: (monotonic_ts, {place_id: place_name})
_places_cache: tuple[float, dict[int, str]] | None = None
_places_cache_ttl_seconds = 60.0


def _invalidate_shifts_for_trip(
    vehicle_id: int,
    loading_timestamp: datetime | None,
    unloading_timestamp: datetime | None,
    cycle_started_at: datetime | None,
    cycle_completed_at: datetime | None,
) -> None:
    """Инвалидировать смены для всех временных точек цикла/рейса (в фоне).

    Args:
        vehicle_id: ID транспорта
        loading_timestamp: Время погрузки
        unloading_timestamp: Время разгрузки
        cycle_started_at: Время начала цикла
        cycle_completed_at: Время завершения цикла
    """

    async def invalidate_shifts() -> None:
        timestamps = [
            loading_timestamp,
            unloading_timestamp,
            cycle_started_at,
            cycle_completed_at,
        ]
        for ts in timestamps:
            if ts:
                await full_shift_state_service.invalidate_shift_by_timestamp(
                    vehicle_id=vehicle_id,
                    timestamp=ts,
                )

    asyncio.create_task(invalidate_shifts())


async def _get_places_names(place_ids: list[int]) -> dict[int, str]:
    """Получить названия мест из graph-service с кэшированием."""
    global _places_cache
    result: dict[int, str] = {}
    now_m = time.monotonic()
    cache: dict[int, str] = {}

    if _places_cache is not None:
        cached_at, cached_items = _places_cache
        if now_m - cached_at < _places_cache_ttl_seconds:
            logger.info("Place cache clear")
            cache = cached_items
        else:
            _places_cache = None

    valid_ids = [pid for pid in place_ids if pid and pid != 0]
    if not valid_ids:
        return result

    unique_ids = list(set(valid_ids))
    uncached_ids = []

    for place_id in unique_ids:
        if place_id in cache:
            result[place_id] = cache[place_id]
        else:
            uncached_ids.append(place_id)

    if not uncached_ids:
        return result

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            url = f"{settings.graph_service_url}/api/places"
            response = await client.get(url, params={"limit": 1000, "offset": 0})

            if response.status_code == 200:
                for place in response.json().get("items", []):
                    pid, name = place.get("id"), place.get("name")
                    if pid and name:
                        cache[pid] = name
                        if pid in uncached_ids:
                            result[pid] = name
                _places_cache = (now_m, cache)
            else:
                logger.error("Get place failed")
    except Exception as e:
        logger.warning("Failed to get places from graph-service", error=str(e))

    return result


def _collect_place_ids(trips: Sequence[Trip]) -> list[int]:
    """Собрать уникальные place_id из списка рейсов."""
    place_ids = set()
    for trip in trips:
        if trip.loading_place_id:
            place_ids.add(trip.loading_place_id)
        if trip.unloading_place_id:
            place_ids.add(trip.unloading_place_id)
    return list(place_ids)


router = APIRouter(prefix="/trips", tags=["trips"])


@router.get(
    "",
    response_model=PaginatedResponse[TripResponse],
    dependencies=[
        Depends(require_permission((Permission.TRIP_EDITOR, Action.VIEW))),
    ],
)
async def list_trips(
    session: SessionDepends,
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    vehicle_id: int = Query(None, description="Фильтр по ID транспорта"),
    task_id: str = Query(None, description="Фильтр по ID задания"),
    trip_type: str = Query(None, description="Фильтр по типу (planned/unplanned)"),
    completed_only: bool = Query(False, description="Только завершенные рейсы (end_time IS NOT NULL)"),
    from_date: datetime = Query(None, description="Дата начала периода"),
    to_date: datetime = Query(None, description="Дата окончания периода"),
) -> Any:
    """Получить список рейсов с пагинацией.

    Фильтрация:
    - vehicle_id: ID транспорта
    - task_id: ID задания
    - status: active, completed, cancelled
    - trip_type: planned, unplanned
    - from_date, to_date: период
    """
    try:
        query = select(Trip)

        if vehicle_id:
            query = query.where(Trip.vehicle_id == vehicle_id)

        if task_id:
            # Связь через task_id в модели Trip
            # В Trip.task_id хранится ID задания для плановых рейсов
            query = query.where(Trip.task_id == task_id)

        # Примечание: в Trip нет поля status, это будет добавлено позже
        # Пока пропускаем фильтр по status
        # if trip_status:
        #     query = query.where(Trip.status == trip_status)

        # Фильтр только завершенных рейсов
        if completed_only:
            query = query.where(Trip.end_time.isnot(None))

        if trip_type:
            query = query.where(Trip.trip_type == trip_type)

        if from_date:
            query = query.where(Trip.start_time >= from_date)

        if to_date:
            query = query.where(Trip.start_time <= to_date)

        # Подсчет
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar_one()

        # Пагинация
        offset = (page - 1) * size
        query = query.order_by(Trip.start_time.desc()).offset(offset).limit(size)
        result = await session.execute(query)
        trips = result.scalars().all()

        # Собираем все place_id для запроса названий
        place_ids = _collect_place_ids(trips)

        # Получаем названия мест и историю изменений остатков параллельно
        places_map = await _get_places_names(place_ids) if place_ids else {}
        place_remaining_history_map = await get_place_remaining_history_by_trips(list(trips), session) if trips else {}

        # Формируем ответы с дополнительными полями
        items = []
        for trip in trips:
            trip_dict = TripResponse.model_validate(trip).model_dump()

            # Добавляем названия мест
            trip_dict["loading_place_name"] = places_map.get(trip.loading_place_id) if trip.loading_place_id else None
            trip_dict["unloading_place_name"] = (
                places_map.get(trip.unloading_place_id) if trip.unloading_place_id else None
            )

            # Вычисляем change_amount для отображения веса
            # Показываем вес, если рейс завершен и есть хотя бы одна запись в Place_remaining_history
            history_list = place_remaining_history_map.get(trip.cycle_id, [])
            is_trip_completed = trip.end_time is not None
            if is_trip_completed and len(history_list) >= 1:
                # Берем абсолютное значение первой записи (или сумму абсолютных значений всех записей)
                # Обычно записей две (loading и unloading), их абсолютные значения одинаковы
                change_amount = abs(history_list[0].change_amount)
                trip_dict["change_amount"] = change_amount

            items.append(TripResponse(**trip_dict))

        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            size=size,
        )

    except Exception as e:
        logger.error("List trips error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get(
    "/analytics",
    response_model=PaginatedResponse[CycleAnalyticsResponse],
)
async def list_trip_analytics(
    session: SessionDepends,
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    vehicle_id: str = Query(None, description="Фильтр по ID транспорта"),
    from_date: datetime = Query(None, description="Дата начала периода"),
    to_date: datetime = Query(None, description="Дата окончания периода"),
) -> Any:
    """Получить список аналитики рейсов с пагинацией.

    Фильтрация:
    - vehicle_id: ID транспорта
    - from_date, to_date: период
    """
    try:
        query = select(CycleAnalytics)

        if vehicle_id:
            query = query.where(CycleAnalytics.vehicle_id == vehicle_id)

        if from_date:
            query = query.where(CycleAnalytics.created_at >= from_date)

        if to_date:
            query = query.where(CycleAnalytics.created_at <= to_date)

        # Подсчет
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar_one()

        # Пагинация
        offset = (page - 1) * size
        query = query.order_by(CycleAnalytics.created_at.desc()).offset(offset).limit(size)
        result = await session.execute(query)
        analytics_list = result.scalars().all()

        return PaginatedResponse.create(
            items=[CycleAnalyticsResponse.model_validate(a) for a in analytics_list],
            total=total,
            page=page,
            size=size,
        )

    except Exception as e:
        logger.error("List trip analytics error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


# Минимальная длительность цикла в минутах
MIN_CYCLE_DURATION_MINUTES = 20

# Нормативные значения для времен погрузки/разгрузки (в минутах)
# Погрузка - через 5 мин после начала цикла
DEFAULT_LOADING_OFFSET_MINUTES = 5
# Разгрузка - за 5 минуты до окончания цикла
DEFAULT_UNLOADING_OFFSET_MINUTES = 5


@router.post(
    "",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_permission((Permission.TRIP_EDITOR, Action.EDIT), (Permission.WORK_TIME_MAP, Action.EDIT))),
    ],
)
async def create_trip(
    trip_data: TripCreate,
    session: SessionDepends,
) -> Any:
    """Создать новый рейс."""
    try:
        # Проверяем vehicle_id
        if not trip_data.vehicle_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="vehicle_id обязателен для создания рейса",
            )
        # Определяем время начала рейса (из loading_timestamp или cycle_started_at)
        start_time = trip_data.loading_timestamp
        if not start_time and trip_data.cycle_started_at:
            start_time = trip_data.cycle_started_at
        if not start_time:
            start_time = cast(datetime, truncate_datetime_to_seconds(datetime.now(UTC)))

        # Определяем время завершения рейса (из unloading_timestamp или cycle_completed_at)
        end_time = trip_data.unloading_timestamp
        if not end_time and trip_data.cycle_completed_at:
            end_time = trip_data.cycle_completed_at

        # Определяем время начала и завершения цикла
        cycle_started_at = trip_data.cycle_started_at or start_time
        cycle_completed_at = trip_data.cycle_completed_at or end_time

        # Проверяем минимальную длительность цикла (20 минут)
        if cycle_started_at and cycle_completed_at:
            cycle_duration = cycle_completed_at - cycle_started_at
            min_duration = timedelta(minutes=MIN_CYCLE_DURATION_MINUTES)

            if cycle_duration < min_duration:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Длительность цикла должна быть не менее {MIN_CYCLE_DURATION_MINUTES} минут. "
                    f"Текущая длительность: {int(cycle_duration.total_seconds() // 60)} минут",
                )
        # Вычисляем нормативные времена погрузки/разгрузки, если не заданы
        loading_timestamp = trip_data.loading_timestamp
        unloading_timestamp = trip_data.unloading_timestamp

        if not loading_timestamp and cycle_started_at:
            loading_timestamp = cycle_started_at + timedelta(minutes=DEFAULT_LOADING_OFFSET_MINUTES)

        if not unloading_timestamp and cycle_completed_at:
            unloading_timestamp = cycle_completed_at - timedelta(minutes=DEFAULT_UNLOADING_OFFSET_MINUTES)

        # Проверяем пересечения с существующими рейсами
        if cycle_started_at is None:
            raise RuntimeError("cycle_started_at must be set at this point")
        try:
            overlap = await check_trip_overlap(
                vehicle_id=trip_data.vehicle_id,
                cycle_started_at=cycle_started_at,
                cycle_completed_at=cycle_completed_at,
                cycle_id=None,  # Новый рейс, нет cycle_id
                db=session,
            )
        except Exception as overlap_error:
            logger.error("Error in check_trip_overlap", error=str(overlap_error), exc_info=True)
            raise

        if overlap:
            logger.info(
                "Trip overlap detected",
                conflicting_cycle_id=overlap["cycle_id"],
                conflicting_cycle_started_at=overlap["cycle_started_at"].isoformat()
                if overlap["cycle_started_at"]
                else None,
                conflicting_cycle_completed_at=overlap["cycle_completed_at"].isoformat()
                if overlap["cycle_completed_at"]
                else None,
            )

            def format_datetime(dt: datetime | None) -> str:
                if not dt:
                    return "не завершён"
                # Конвертируем в таймзону из настроек и форматируем как "21.01.2026 18:01"
                try:
                    tz = ZoneInfo(settings.timezone)
                    if dt.tzinfo is None:
                        # Если datetime наивный, считаем что это UTC
                        dt = dt.replace(tzinfo=UTC)
                    dt_local = dt.astimezone(tz)
                    return dt_local.strftime("%d.%m.%Y %H:%M")
                except Exception:
                    # Fallback на исходный формат если что-то пошло не так
                    return dt.strftime("%d.%m.%Y %H:%M")

            started_str = format_datetime(overlap["cycle_started_at"])
            completed_str = format_datetime(overlap["cycle_completed_at"])
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Не удалось создать новый рейс из-за пересечения "
                f"с рейсом {overlap['cycle_id']} ({started_str} - {completed_str})",
            ) from None

        if start_time is None:
            raise RuntimeError("start_time must be set at this point")

        # Создаем Trip (дочерняя сущность через JTI)
        # SQLAlchemy автоматически создаст запись в таблице cycles при сохранении Trip
        cycle_id = generate_uuid()

        # Создаем Trip только с его собственными полями
        # При JTI SQLAlchemy не принимает поля родительского класса в конструкторе дочернего класса
        try:
            trip = Trip(
                cycle_id=cycle_id,
                trip_type="unplanned",  # По умолчанию, так как в контракте нет trip_type
                start_time=start_time,
                end_time=end_time,
                loading_place_id=trip_data.loading_place_id,
                loading_timestamp=loading_timestamp,
                unloading_place_id=trip_data.unloading_place_id,
                unloading_timestamp=unloading_timestamp,
            )
            logger.info("Trip object created", cycle_id=cycle_id, vehicle_id=trip_data.vehicle_id)
        except Exception as trip_create_error:
            logger.error("Error creating Trip object", error=str(trip_create_error), exc_info=True)
            raise

        # ВАЖНО: При JTI нужно явно устанавливать поля родительского класса после создания объекта
        # SQLAlchemy не наследует их автоматически при создании дочернего объекта
        trip.vehicle_id = trip_data.vehicle_id
        trip.task_id = None
        trip.shift_id = None
        trip.from_place_id = trip_data.loading_place_id
        trip.to_place_id = trip_data.unloading_place_id
        trip.cycle_started_at = cycle_started_at
        trip.cycle_completed_at = cycle_completed_at
        trip.cycle_status = "completed"
        trip.cycle_type = "normal"
        trip.entity_type = "trip"
        trip.source = "dispatcher"  # Рейс создан через API диспетчера

        session.add(trip)

        await session.flush()
        await bulk_update_trips_cycle_num(trip.vehicle_id, trip.start_time, session)

        await session.commit()
        await session.refresh(trip)

        # Создаём статусы cycle_state_history на основе временных меток рейса
        await create_trip_state_history(trip, session)
        await session.commit()

        # Создаем две записи истории остатков по месту (loading/unloading)
        if trip_data.change_amount is not None:
            if not trip.loading_place_id or not trip.unloading_place_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Для создания истории остатков нужны loading_place_id и unloading_place_id",
                )
            if not loading_timestamp or not unloading_timestamp:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Для создания истории остатков нужны loading_timestamp и unloading_timestamp",
                )
            change_amount = abs(trip_data.change_amount)

            # loading: уменьшение остатка
            await place_remaining_service.create_history(
                db=session,
                data=PlaceRemainingHistoryCreate(
                    place_id=trip.loading_place_id,
                    change_type=RemainingChangeTypeEnum.loading,
                    change_amount=-change_amount,
                    timestamp=loading_timestamp,
                    cycle_id=trip.cycle_id,
                    task_id=trip.task_id,
                    shift_id=trip.shift_id,
                    vehicle_id=trip.vehicle_id,
                    source="dispatcher",
                ),
                notify_graph=True,
            )

            # unloading: увеличение остатка
            await place_remaining_service.create_history(
                db=session,
                data=PlaceRemainingHistoryCreate(
                    place_id=trip.unloading_place_id,
                    change_type=RemainingChangeTypeEnum.unloading,
                    change_amount=change_amount,
                    timestamp=unloading_timestamp,
                    cycle_id=trip.cycle_id,
                    task_id=trip.task_id,
                    shift_id=trip.shift_id,
                    vehicle_id=trip.vehicle_id,
                    source="dispatcher",
                ),
                notify_graph=True,
            )

        trip_response = TripResponse.model_validate(trip)

        # Публикуем событие создания рейса для real-time обновлений
        await redis_client.publish_trip_event(
            event_type="created",
            trip_data=trip_response.model_dump(mode="json"),
        )

        # Публикуем событие history_changed для обновления UI
        await publish_trip_history_changed_event(trip)

        # Инвалидировать смены для всех временных точек цикла/рейса (в фоне)
        _invalidate_shifts_for_trip(
            vehicle_id=trip.vehicle_id,
            loading_timestamp=trip.loading_timestamp,
            unloading_timestamp=trip.unloading_timestamp,
            cycle_started_at=trip.cycle_started_at,
            cycle_completed_at=trip.cycle_completed_at,
        )

        return trip_response

    except HTTPException:
        # HTTPException (включая 409 Conflict) пробрасываем без изменений
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        logger.error("Create trip error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании рейса: {str(e)}",
        ) from e


@router.get(
    "/{trip_id}",
    response_model=TripResponse,
)
async def get_trip(
    trip_id: str,
    session: SessionDepends,
) -> Any:
    """Получить цикл/рейс по ID (trip_id = cycle_id в JTI)."""
    try:
        cycle_query = select(Cycle).where(Cycle.cycle_id == trip_id)
        cycle_result = await session.execute(cycle_query)
        cycle = cycle_result.scalar_one_or_none()

        if not cycle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Цикл/рейс {trip_id} не найден",
            )
        trip_query = select(Trip).where(Trip.cycle_id == trip_id)
        trip_result = await session.execute(trip_query)
        trip = trip_result.scalar_one_or_none()

        place_ids = []
        if cycle.from_place_id:
            place_ids.append(cycle.from_place_id)
        if cycle.to_place_id:
            place_ids.append(cycle.to_place_id)
        if trip and trip.loading_place_id:
            place_ids.append(trip.loading_place_id)
        if trip and trip.unloading_place_id:
            place_ids.append(trip.unloading_place_id)

        places_map = await _get_places_names(place_ids) if place_ids else {}

        response_data = {
            # Поля Cycle
            "cycle_id": cycle.cycle_id,
            "vehicle_id": cycle.vehicle_id,
            "task_id": cycle.task_id,
            "shift_id": cycle.shift_id,
            "from_place_id": cycle.from_place_id,
            "to_place_id": cycle.to_place_id,
            "cycle_started_at": cycle.cycle_started_at,
            "cycle_completed_at": cycle.cycle_completed_at,
            "source": cycle.source,
            "created_at": cycle.created_at,
            "updated_at": cycle.updated_at,
            # Поля Trip (null если Trip не существует)
            "cycle_num": trip.cycle_num if trip else None,
            "trip_type": trip.trip_type if trip else None,
            "start_time": trip.start_time if trip else None,
            "end_time": trip.end_time if trip else None,
            "loading_place_id": trip.loading_place_id if trip else None,
            "unloading_place_id": trip.unloading_place_id if trip else None,
            "loading_tag": trip.loading_tag if trip else None,
            "unloading_tag": trip.unloading_tag if trip else None,
            "loading_timestamp": trip.loading_timestamp if trip else None,
            "unloading_timestamp": trip.unloading_timestamp if trip else None,
            # Названия мест из Trip
            "loading_place_name": places_map.get(trip.loading_place_id) if trip and trip.loading_place_id else None,
            "unloading_place_name": places_map.get(trip.unloading_place_id)
            if trip and trip.unloading_place_id
            else None,
        }

        return TripResponse.model_validate(response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get trip error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.put(
    "/{trip_id}",
    response_model=TripResponse,
    dependencies=[Depends(require_permission((Permission.TRIP_EDITOR, Action.EDIT)))],
)
async def update_trip(
    trip_id: str,
    trip_data: TripUpdate,
    session: SessionDepends,
) -> Any:
    """Обновить рейс."""
    try:
        # Получаем рейс
        query = select(Trip).where(Trip.cycle_id == trip_id)
        result = await session.execute(query)
        trip = result.scalar_one_or_none()

        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Рейс {trip_id} не найден",
            )
        # Получаем родительский Cycle
        cycle_query = select(Cycle).where(Cycle.cycle_id == trip_id)
        cycle_result = await session.execute(cycle_query)
        cycle = cycle_result.scalar_one_or_none()

        if not cycle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Цикл {trip_id} не найден",
            )
        # Сохраняем старые значения мест для пересчета остатков
        old_loading_place_id = trip.loading_place_id
        old_unloading_place_id = trip.unloading_place_id

        # Обновляем поля Trip
        update_data = trip_data.model_dump(exclude_unset=True)

        # Валидация timestamp полей - проверяем границы статусов
        timestamp_fields = {
            "loading_timestamp": "Время начала погрузки",
            "unloading_timestamp": "Время начала разгрузки",
            "cycle_started_at": "Время начала цикла",
            "cycle_completed_at": "Время завершения цикла",
        }

        vehicle_id = cycle.vehicle_id

        for field_name, field_display_name in timestamp_fields.items():
            if field_name in update_data:
                new_value = update_data[field_name]
                if new_value:
                    # Получаем старое значение для этого поля
                    old_value = getattr(
                        trip if field_name in ["loading_timestamp", "unloading_timestamp"] else cycle,
                        field_name,
                        None,
                    )

                    # Если значение изменилось, проверяем границы статусов
                    # Находим соседние статусы для старого значения (границы, в которых оно находилось)
                    if old_value and old_value != new_value:
                        # Находим предыдущий статус (с timestamp < старого значения)
                        prev_query = (
                            select(CycleStateHistory)
                            .where(
                                CycleStateHistory.vehicle_id == vehicle_id,
                                CycleStateHistory.timestamp < old_value,
                            )
                            .order_by(desc(CycleStateHistory.timestamp))
                            .limit(1)
                        )
                        prev_result = await session.execute(prev_query)
                        prev_status = prev_result.scalar_one_or_none()

                        # Находим следующий статус (с timestamp > старого значения)
                        next_query = (
                            select(CycleStateHistory)
                            .where(
                                CycleStateHistory.vehicle_id == vehicle_id,
                                CycleStateHistory.timestamp > old_value,
                            )
                            .order_by(CycleStateHistory.timestamp)
                            .limit(1)
                        )
                        next_result = await session.execute(next_query)
                        next_status = next_result.scalar_one_or_none()

                        # Проверяем границы
                        if prev_status and new_value <= prev_status.timestamp:
                            status_display_name = await get_status_display_name(prev_status.state)
                            time_str = format_time_for_message(prev_status.timestamp)
                            new_time_str = format_time_for_message(new_value)
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Значение поля '{field_display_name}' ({new_time_str}) "
                                f"пересекается со статусом '{status_display_name}' ({time_str})",
                            )
                        if next_status and new_value >= next_status.timestamp:
                            status_display_name = await get_status_display_name(next_status.state)
                            time_str = format_time_for_message(next_status.timestamp)
                            new_time_str = format_time_for_message(new_value)
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Значение поля '{field_display_name}' ({new_time_str}) "
                                f"пересекается со статусом '{status_display_name}' ({time_str})",
                            )
        # Сохраняем старые значения начала и окончания цикла до обновления
        old_cycle_started_at = cycle.cycle_started_at if "cycle_started_at" in update_data else None
        old_cycle_completed_at = cycle.cycle_completed_at if "cycle_completed_at" in update_data else None

        # Обновляем поля Trip (исключаем cycle_num - он не должен изменяться при обновлении)
        for key, value in update_data.items():
            if hasattr(trip, key) and key != "cycle_num":
                setattr(trip, key, value)

        # Обновляем поля Cycle
        if "vehicle_id" in update_data:
            cycle.vehicle_id = update_data["vehicle_id"]
        if "task_id" in update_data:
            tid = update_data.get("task_id")
            cycle.task_id = str(tid) if tid is not None else None
        if "shift_id" in update_data:
            cycle.shift_id = update_data.get("shift_id")
        if "loading_place_id" in update_data:
            cycle.from_place_id = update_data["loading_place_id"]
        if "unloading_place_id" in update_data:
            cycle.to_place_id = update_data["unloading_place_id"]
        if "cycle_started_at" in update_data:
            cycle.cycle_started_at = update_data["cycle_started_at"]
        if "cycle_completed_at" in update_data:
            cycle.cycle_completed_at = update_data["cycle_completed_at"]

        # При обновлении через API диспетчера устанавливаем source = "dispatcher"
        cycle.source = "dispatcher"

        # Фиксируем обновление рейса/цикла
        await session.commit()
        await session.refresh(trip)
        await session.refresh(cycle)

        # Обновляем существующие статусы cycle_state_history на основе временных меток рейса
        await update_trip_state_history(
            trip,
            session,
            old_cycle_completed_at=old_cycle_completed_at,
            old_cycle_started_at=old_cycle_started_at,
        )

        # --------------- Обновление мест погрузки/разгрузки в истории остатков ----------------
        # Проверяем, изменились ли места погрузки/разгрузки
        new_loading_place_id = trip.loading_place_id
        new_unloading_place_id = trip.unloading_place_id

        loading_place_changed = (
            old_loading_place_id is not None
            and new_loading_place_id is not None
            and old_loading_place_id != new_loading_place_id
        )
        unloading_place_changed = (
            old_unloading_place_id is not None
            and new_unloading_place_id is not None
            and old_unloading_place_id != new_unloading_place_id
        )

        if loading_place_changed or unloading_place_changed:
            # Проверяем, что рейс завершен (для пересчета остатков)
            if not (trip.end_time or cycle.cycle_completed_at):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Изменение мест погрузки/разгрузки возможно только для завершенных рейсов",
                )
            # Используем сервис остатков по местам для обновления истории и пересчета остатков
            await place_remaining_service.update_places_for_trip(
                db=session,
                cycle_id=trip.cycle_id,
                old_loading_place_id=old_loading_place_id if loading_place_changed else None,
                new_loading_place_id=new_loading_place_id if loading_place_changed else None,
                old_unloading_place_id=old_unloading_place_id if unloading_place_changed else None,
                new_unloading_place_id=new_unloading_place_id if unloading_place_changed else None,
            )

        # --------------- Пересчет остатков по новому весу/объему ----------------
        # Пересчет допустим только для завершенных рейсов
        new_change_amount = update_data.get("change_amount")
        if new_change_amount is not None:
            if not (trip.end_time or cycle.cycle_completed_at):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Пересчет остатков по change_amount возможен только для завершенных рейсов",
                )
            # Используем сервис остатков по местам для обновления change_amount и пересчета остатков
            await place_remaining_service.update_change_amount_for_trip(
                db=session,
                cycle_id=trip.cycle_id,
                new_change_amount=new_change_amount,
            )

        await session.commit()

        trip_response = TripResponse.model_validate(trip)

        # Публикуем событие обновления рейса для real-time обновлений
        await redis_client.publish_trip_event(
            event_type="updated",
            trip_data=trip_response.model_dump(mode="json"),
        )

        # Публикуем событие history_changed для обновления UI
        await publish_trip_history_changed_event(trip)

        # Инвалидировать смены для всех временных точек цикла/рейса (в фоне)
        _invalidate_shifts_for_trip(
            vehicle_id=cycle.vehicle_id,
            loading_timestamp=trip.loading_timestamp,
            unloading_timestamp=trip.unloading_timestamp,
            cycle_started_at=cycle.cycle_started_at,
            cycle_completed_at=cycle.cycle_completed_at,
        )

        return trip_response

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("Update trip error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении рейса: {str(e)}",
        ) from e


@router.delete(
    "/{trip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission((Permission.TRIP_EDITOR, Action.EDIT)))],
)
async def delete_trip(
    trip_id: str,
    session: SessionDepends,
) -> None:
    """Удалить рейс (soft delete через изменение статуса цикла)."""
    try:
        # Получаем рейс
        query = select(Trip).where(Trip.cycle_id == trip_id)
        result = await session.execute(query)
        trip = result.scalar_one_or_none()

        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Рейс {trip_id} не найден",
            )
        # Получаем родительский Cycle
        cycle_query = select(Cycle).where(Cycle.cycle_id == trip_id)
        cycle_result = await session.execute(cycle_query)
        cycle = cycle_result.scalar_one_or_none()

        if not cycle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Цикл {trip_id} не найден",
            )
        # Сохраняем данные для публикации события до удаления
        vehicle_id = trip.vehicle_id
        trip_timestamp = trip.loading_timestamp or trip.cycle_started_at or trip.start_time

        # Удаляем связанные статусы из cycle_state_history
        deleted_states_count = await delete_trip_state_history(trip_id, session)
        logger.info(
            "Deleted state history for trip",
            trip_id=trip_id,
            deleted_count=deleted_states_count,
        )

        # Создаем статус "no_data" (Нет данных) после удаления цикла
        if trip.cycle_started_at is not None:
            await create_no_data_status_after_cycle_deletion(
                vehicle_id=vehicle_id,
                cycle_started_at=trip.cycle_started_at,
                db=session,
            )

        # Удаляем записи об остатках по cycle_id и пересчитываем остатки для затронутых мест
        try:
            await place_remaining_service.delete_by_cycle_id(
                db=session,
                cycle_id=trip_id,
            )
            logger.info(
                "Deleted place remaining history for trip",
                trip_id=trip_id,
            )
        except Exception as e:
            logger.error(
                "Failed to delete place remaining history for trip",
                trip_id=trip_id,
                error=str(e),
                exc_info=True,
            )
            # Продолжаем удаление Trip даже если не удалось удалить записи об остатках

        # Физическое удаление: сначала удаляем Trip (дочерняя таблица), потом Cycle (родительская)
        result_trip = cast(CursorResult[Any], await session.execute(delete(Trip).where(Trip.cycle_id == trip_id)))
        result_cycle = cast(CursorResult[Any], await session.execute(delete(Cycle).where(Cycle.cycle_id == trip_id)))

        await bulk_update_trips_cycle_num(cycle.vehicle_id, trip.start_time, session)

        logger.info(
            "Delete statements executed",
            trip_id=trip_id,
            trip_rows_deleted=result_trip.rowcount,
            cycle_rows_deleted=result_cycle.rowcount,
        )

        await session.commit()

        logger.info("Trip deleted successfully", trip_id=trip_id)

        # Публикуем событие удаления рейса для real-time обновлений
        await redis_client.publish_trip_event(
            event_type="deleted",
            trip_data={"cycle_id": trip_id},
        )

        # Публикуем событие history_changed для обновления UI
        if trip_timestamp:
            shift_info = await get_shift_info_for_timestamp(trip_timestamp, vehicle_id)
            if shift_info:
                await _publish_history_changed_event(
                    vehicle_id=vehicle_id,
                    shift_date=shift_info["shift_date"],
                    shift_num=shift_info["shift_num"],
                )

        # Инвалидировать смены для всех временных точек цикла/рейса (в фоне)
        _invalidate_shifts_for_trip(
            vehicle_id=vehicle_id,
            loading_timestamp=trip.loading_timestamp,
            unloading_timestamp=trip.unloading_timestamp,
            cycle_started_at=cycle.cycle_started_at,
            cycle_completed_at=cycle.cycle_completed_at,
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("Delete trip error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении рейса: {str(e)}",
        ) from e


@router.get(
    "/{trip_id}/state-history",
    response_model=PaginatedResponse[CycleStateHistoryResponse],
)
async def get_trip_state_history(
    session: SessionDepends,
    trip_id: str,
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(50, ge=1, le=200, description="Размер страницы"),
) -> Any:
    """Получить историю состояний рейса (trip_id = cycle_id)."""
    try:
        query = select(CycleStateHistory).where(
            CycleStateHistory.cycle_id == trip_id,
        )

        # Подсчет
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar_one()

        # Пагинация
        offset = (page - 1) * size
        query = query.order_by(CycleStateHistory.timestamp.desc()).offset(offset).limit(size)
        result = await session.execute(query)
        history = result.scalars().all()

        return PaginatedResponse.create(
            items=[CycleStateHistoryResponse.model_validate(h) for h in history],
            total=total,
            page=page,
            size=size,
        )

    except Exception as e:
        logger.error("Get trip state history error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get(
    "/{trip_id}/tag-history",
    response_model=PaginatedResponse[CycleTagHistoryResponse],
)
async def get_trip_tag_history(
    session: SessionDepends,
    trip_id: str,
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(50, ge=1, le=200, description="Размер страницы"),
) -> Any:
    """Получить историю меток рейса (trip_id = cycle_id)."""
    try:
        query = select(CycleTagHistory).where(
            CycleTagHistory.cycle_id == trip_id,
        )

        # Подсчет
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar_one()

        # Пагинация
        offset = (page - 1) * size
        query = query.order_by(CycleTagHistory.timestamp.desc()).offset(offset).limit(size)
        result = await session.execute(query)
        history = result.scalars().all()

        return PaginatedResponse.create(
            items=[CycleTagHistoryResponse.model_validate(h) for h in history],
            total=total,
            page=page,
            size=size,
        )

    except Exception as e:
        logger.error("Get trip tag history error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get(
    "/{trip_id}/analytics",
    response_model=CycleAnalyticsResponse,
)
async def get_trip_analytics(
    trip_id: str,
    session: SessionDepends,
) -> Any:
    """Получить аналитику рейса."""
    try:
        query = select(CycleAnalytics).where(CycleAnalytics.cycle_id == trip_id)
        result = await session.execute(query)
        analytics = result.scalar_one_or_none()

        if not analytics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Аналитика для рейса {trip_id} не найдена",
            )
        return analytics

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get trip analytics error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.post(
    "/{trip_id}/analytics",
    response_model=CycleAnalyticsResponse,
)
async def create_trip_analytics_endpoint(
    trip_id: str,
    session: SessionDepends,
) -> Any:
    """Создать аналитику для рейса."""
    try:
        from app.services.analytics import finalize_trip_analytics

        analytics = await finalize_trip_analytics(trip_id, session)

        if not analytics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Рейс {trip_id} не найден или не завершен",
            )
        return analytics

    except Exception as e:
        logger.error("Create trip analytics error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e
