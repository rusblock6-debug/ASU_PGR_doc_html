"""State History Service - управление историей состояний в серверном режиме.

Предоставляет функции для batch создания/редактирования cycle_state_history.

Основные функции:
- batch_upsert_state_history() - batch создание/редактирование записей
- delete_state_history() - удаление записи с очисткой связанных данных
"""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import httpx
from loguru import logger
from sqlalchemy import delete, desc, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.event_log import (
    CycleStateHistoryBatchItem,
    CycleStateHistoryBatchResponse,
    CycleStateHistoryBatchResultItem,
    StateHistoryDeleteResponse,
)
from app.core.config import settings
from app.core.redis_client import redis_client
from app.database.base import generate_uuid_vehicle_id
from app.database.models import Cycle, CycleStateHistory, Trip
from app.utils.datetime_utils import format_datetime_for_message, truncate_datetime_to_seconds


async def get_status_display_name(system_name: str) -> str:
    """Получить display_name статуса из enterprise-service по system_name.

    Returns:
        display_name статуса или system_name, если не удалось получить
    """
    info = await get_status_info(system_name)
    return info["display_name"] if info else system_name


async def get_status_info(system_name: str) -> dict[str, Any] | None:
    """Получить информацию о статусе из enterprise-service по system_name.

    Returns:
        Словарь с display_name и is_work_status или None, если не удалось получить
    """
    try:
        url = f"{settings.enterprise_service_url}/api/statuses/by-system-name/{system_name}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)

            if response.status_code == 200:
                data = response.json()
                return {
                    "display_name": data.get("display_name", system_name),
                    "is_work_status": data.get("is_work_status", False),
                }
    except Exception as e:
        logger.error(
            "Error getting status info from enterprise-service",
            system_name=system_name,
            error=str(e),
        )
    return None


async def _publish_history_changed_event(vehicle_id: int, shift_date: str, shift_num: int) -> None:
    """Публикация события об изменении истории статусов.

    Args:
        vehicle_id: ID транспорта
        shift_date: Дата смены в формате YYYY-MM-DD
        shift_num: Номер смены
    """
    try:
        import json

        event_data = {
            "event_type": "history_changed",
            "vehicle_id": vehicle_id,
            "shift_date": shift_date,
            "shift_num": shift_num,
        }

        channel = f"trip-service:vehicle:{vehicle_id}:events"
        if redis_client.redis is None:
            raise RuntimeError("Redis client is not connected")
        await redis_client.redis.publish(channel, json.dumps(event_data))

        logger.debug(
            "📡 History changed event published to Redis",
            vehicle_id=vehicle_id,
            shift_date=shift_date,
            shift_num=shift_num,
            channel=channel,
            event_data=event_data,
        )

    except Exception as e:
        logger.error(
            "Failed to publish history_changed event",
            vehicle_id=vehicle_id,
            shift_date=shift_date,
            shift_num=shift_num,
            error=str(e),
        )


async def get_shift_info_for_timestamp(timestamp: datetime | None, vehicle_id: int) -> dict[str, Any] | None:
    """Получить информацию о смене для timestamp через enterprise-service.

    Args:
        timestamp: Время для определения смены
        vehicle_id: ID транспорта (для логов)

    Returns:
        Словарь с shift_date и shift_num или None
    """
    if timestamp is None:
        return None
    try:
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        async with httpx.AsyncClient() as client:
            utc_timestamp = timestamp.astimezone(UTC).replace(tzinfo=None)
            response = await client.get(
                f"{settings.enterprise_service_url}/api/shift-service/get-shift-info-by-timestamp",
                params={"timestamp": utc_timestamp.isoformat()},
                timeout=5.0,
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    "Failed to get shift info from enterprise-service",
                    vehicle_id=vehicle_id,
                    timestamp=timestamp.isoformat(),
                    status_code=response.status_code,
                    response_text=response.text,
                )
                return None
    except Exception as e:
        logger.error(
            "Error getting shift info from enterprise-service",
            vehicle_id=vehicle_id,
            timestamp=timestamp.isoformat(),
            error=str(e),
        )
        return None


# Матрица  переходов состояний
CYCLE_START_STATES_FROM_IDLE = {"moving_empty", "stopped_empty", "loading"}


def determine_cycle_action(
    from_state: str | None,
    to_state: str,
    has_active_cycle: bool,
) -> str | None:
    """Определить действие с циклом при переходе состояния.

    Args:
        from_state: Текущее состояние
        to_state: Целевое состояние
        has_active_cycle: Есть ли активный цикл

    Returns:
        str или None: "start_cycle", "complete_cycle", None
    """
    if from_state == "unloading":
        if to_state == "idle":
            return "complete_cycle"
        elif to_state == "moving_empty":
            return "complete_and_start_cycle"

    if from_state == "idle" or from_state is None:
        if to_state in CYCLE_START_STATES_FROM_IDLE and not has_active_cycle:
            return "start_cycle"

    return None


async def get_last_state_for_vehicle(
    vehicle_id: int,
    before_timestamp: datetime,
    db: AsyncSession,
) -> CycleStateHistory | None:
    """Получить последнее состояние для транспорта до указанного времени.

    Args:
        vehicle_id: ID транспорта
        before_timestamp: Время, до которого искать
        db: Database session

    Returns:
        CycleStateHistory или None
    """
    query = (
        select(CycleStateHistory)
        .where(CycleStateHistory.vehicle_id == vehicle_id)
        .where(CycleStateHistory.timestamp < before_timestamp)
        .order_by(desc(CycleStateHistory.timestamp))
        .limit(1)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_next_state_timestamp(
    vehicle_id: int,
    after_timestamp: datetime,
    db: AsyncSession,
) -> datetime | None:
    """Получить timestamp следующего статуса после указанного времени.

    Args:
        vehicle_id: ID транспорта
        after_timestamp: Время, после которого ищем следующий статус
        db: Database session

    Returns:
        Optional[datetime]: timestamp следующего статуса или None, если его нет
    """
    query = (
        select(CycleStateHistory.timestamp)
        .where(CycleStateHistory.vehicle_id == vehicle_id)
        .where(CycleStateHistory.timestamp > after_timestamp)
        .order_by(CycleStateHistory.timestamp)
        .limit(1)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_active_cycle_for_vehicle(
    vehicle_id: int,
    db: AsyncSession,
) -> Cycle | None:
    """Получить активный цикл для транспорта.

    Берет последний цикл (по created_at) для данного vehicle_id
    и проверяет, находится ли он в статусе in_progress.
    Если да - возвращает его, иначе - None.

    Args:
        vehicle_id: ID транспорта
        db: Database session

    Returns:
        Cycle или None
    """
    query = select(Cycle).where(Cycle.vehicle_id == vehicle_id).order_by(desc(Cycle.created_at)).limit(1)
    result = await db.execute(query)
    cycle = result.scalar_one_or_none()

    if cycle and cycle.cycle_status == "in_progress":
        return cycle

    return None


async def get_active_cycle_for_vehicle_within_last_hour(
    vehicle_id: int,
    reference_timestamp: datetime,
    db: AsyncSession,
) -> Cycle | None:
    """Получить активный цикл для транспорта только в рамках последнего часа.

    Берет последний цикл (по created_at) для vehicle_id в статусе in_progress
    и проверяет, что cycle_started_at >= reference_timestamp - 1 час.
    Иначе возвращает None.

    Args:
        vehicle_id: ID транспорта
        reference_timestamp: Время, относительно которого считается «последний час»
        db: Database session

    Returns:
        Cycle или None
    """
    threshold = reference_timestamp - timedelta(hours=1)
    if threshold.tzinfo is None:
        threshold = threshold.replace(tzinfo=UTC)

    query = (
        select(Cycle)
        .where(Cycle.vehicle_id == vehicle_id)
        .where(Cycle.cycle_status == "in_progress")
        .order_by(desc(Cycle.created_at))
        .limit(1)
    )
    result = await db.execute(query)
    cycle = result.scalar_one_or_none()

    if not cycle or not cycle.cycle_started_at:
        return None

    started = cycle.cycle_started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    if started < threshold:
        return None

    return cycle


async def create_cycle_for_state(
    vehicle_id: int,
    timestamp: datetime,
    from_place_id: int | None = None,
    db: AsyncSession | None = None,
) -> str:
    """Создать новый цикл для состояния.

    Args:
        vehicle_id: ID транспорта
        timestamp: Время начала цикла
        from_place_id: ID места начала (опционально)
        db: Database session

    Returns:
        cycle_id: ID созданного цикла
    """
    if not db:
        raise ValueError("Database session is required")

    cycle = Cycle(
        vehicle_id=vehicle_id,
        from_place_id=from_place_id,
        cycle_started_at=timestamp,
        cycle_status="in_progress",
        cycle_type="normal",
        source="dispatcher",
    )

    db.add(cycle)
    await db.flush()

    logger.info(
        "Cycle created via batch operation",
        vehicle_id=vehicle_id,
        cycle_id=cycle.cycle_id,
        timestamp=timestamp.isoformat(),
    )

    return cycle.cycle_id


async def complete_cycle(
    cycle_id: str,
    timestamp: datetime,
    to_place_id: int | None = None,
    db: AsyncSession | None = None,
) -> bool:
    """Завершить цикл.

    Args:
        cycle_id: ID цикла
        timestamp: Время завершения
        to_place_id: ID места завершения (опционально)
        db: Database session

    Returns:
        bool: Успех операции
    """
    if not db:
        return False

    query = select(Cycle).where(Cycle.cycle_id == cycle_id)
    result = await db.execute(query)
    cycle = result.scalar_one_or_none()

    if not cycle:
        logger.warning("Cycle not found for completion", cycle_id=cycle_id)
        return False

    cycle.cycle_completed_at = timestamp
    cycle.to_place_id = to_place_id
    cycle.cycle_status = "completed"

    logger.info(
        "Cycle completed via batch operation",
        cycle_id=cycle_id,
        timestamp=timestamp.isoformat(),
    )

    return True


async def _ensure_trip_for_loading(
    cycle_id: str,
    timestamp: datetime,
    db: AsyncSession,
) -> None:
    """Создать (начать) рейс для цикла при Погрузке, если его ещё нет.

    Заполняет start_time и loading_timestamp переданным временем.
    """
    trip_query = select(Trip).where(Trip.cycle_id == cycle_id)
    trip_result = await db.execute(trip_query)
    if trip_result.scalar_one_or_none() is not None:
        return

    await db.execute(
        insert(Trip).values(
            cycle_id=cycle_id,
            trip_type="unplanned",
            start_time=timestamp,
            loading_timestamp=timestamp,
            cycle_num=1,
        ),
    )
    await db.execute(
        update(Cycle).where(Cycle.cycle_id == cycle_id).values(entity_type="trip"),
    )
    await db.flush()
    logger.debug(
        "Trip created for loading (batch)",
        cycle_id=cycle_id,
        timestamp=timestamp.isoformat(),
    )


async def batch_upsert_state_history(
    vehicle_id: int,
    items: list[CycleStateHistoryBatchItem],
    db: AsyncSession,
) -> CycleStateHistoryBatchResponse:
    """Batch создание/редактирование записей cycle_state_history.

    Все операции выполняются в одной транзакции.
    При ошибке - откат всей транзакции.

    Args:
        vehicle_id: ID транспорта
        items: Список элементов для создания/редактирования
        db: Database session

    Returns:
        CycleStateHistoryBatchResponse с результатами
    """
    results: list[CycleStateHistoryBatchResultItem] = []
    cycles_created = 0
    cycles_completed = 0

    try:
        # Сортируем элементы по timestamp для корректной валидации переходов
        sorted_items = sorted(items, key=lambda x: x.timestamp or datetime.min)
        first_item = sorted_items[0]
        last_state = await get_last_state_for_vehicle(
            vehicle_id=vehicle_id,
            before_timestamp=first_item.timestamp or datetime.now(UTC),
            db=db,
        )
        current_state = last_state.state if last_state else None

        for item in sorted_items:
            if item.id:
                result = await _update_existing_record(
                    record_id=item.id,
                    timestamp=item.timestamp or datetime.now(UTC),
                    new_state=item.system_name,
                    is_end_of_cycle=item.is_end_of_cycle,
                    db=db,
                )
                results.append(result)
            else:
                # Разделение интервала на КРВ
                ts = item.timestamp
                if ts:
                    result = await _create_new_record(
                        vehicle_id=vehicle_id,
                        timestamp=ts,
                        state=item.system_name,
                        cycle_id=item.cycle_id,
                        cycle_action="none",
                        db=db,
                    )
                    results.append(result)
                else:
                    ts = cast(datetime, truncate_datetime_to_seconds(datetime.now(UTC)))
                    # Создание нового статуса — применяем правила циклов (активный цикл в рамках последнего часа)
                    active_cycle = await get_active_cycle_for_vehicle_within_last_hour(
                        vehicle_id=vehicle_id,
                        reference_timestamp=ts,
                        db=db,
                    )
                    cycle_id: str | None = None
                    cycle_action = "none"

                    if active_cycle:
                        if current_state == "unloading":
                            # Статус после Разгрузки — завершаем цикл
                            await complete_cycle(
                                cycle_id=active_cycle.cycle_id,
                                timestamp=ts,
                                db=db,
                            )
                            cycles_completed += 1
                            cycle_action = "completed"
                            if item.system_name == "moving_empty":
                                # Тот же timestamp — создаём новый цикл; у статуса cycle_id нового цикла
                                cycle_id = await create_cycle_for_state(
                                    vehicle_id=vehicle_id,
                                    timestamp=ts,
                                    db=db,
                                )
                                cycles_created += 1
                                cycle_action = "created"
                            # иначе cycle_id у статуса отсутствует (остаётся None)
                        elif item.system_name == "loading":
                            # Погрузка — создаём (начинаем) рейс, start_time и loading_timestamp = ts
                            await _ensure_trip_for_loading(
                                cycle_id=active_cycle.cycle_id,
                                timestamp=ts,
                                db=db,
                            )
                            cycle_id = active_cycle.cycle_id
                        elif item.system_name == "unloading":
                            # Разгрузка — заполняем unloading_timestamp (и end_time) у рейса
                            trip_query = select(Trip).where(Trip.cycle_id == active_cycle.cycle_id)
                            trip_result = await db.execute(trip_query)
                            trip = trip_result.scalar_one_or_none()
                            if trip:
                                trip.unloading_timestamp = ts
                                trip.end_time = ts
                                logger.debug(
                                    "Updated trip unloading_timestamp (create)",
                                    cycle_id=active_cycle.cycle_id,
                                    timestamp=ts.isoformat(),
                                )
                            cycle_id = active_cycle.cycle_id
                        else:
                            cycle_id = active_cycle.cycle_id
                    else:
                        if item.system_name == "moving_empty":
                            cycle_id = await create_cycle_for_state(
                                vehicle_id=vehicle_id,
                                timestamp=ts,
                                db=db,
                            )
                            cycles_created += 1
                            cycle_action = "created"

                    result = await _create_new_record(
                        vehicle_id=vehicle_id,
                        timestamp=ts,
                        state=item.system_name,
                        cycle_id=cycle_id,
                        cycle_action=cycle_action,
                        db=db,
                    )
                    results.append(result)

                current_state = item.system_name

        # Коммитим все изменения
        await db.commit()

        logger.info(
            "Batch state history upsert completed",
            vehicle_id=vehicle_id,
            items_count=len(items),
            cycles_created=cycles_created,
            cycles_completed=cycles_completed,
        )

        # Публикуем событие об изменении истории для смены первого элемента
        first_item = sorted_items[0]
        first_ts = first_item.timestamp or datetime.now(UTC)
        shift_info = await get_shift_info_for_timestamp(first_ts, vehicle_id)
        if shift_info:
            await _publish_history_changed_event(
                vehicle_id=vehicle_id,
                shift_date=shift_info["shift_date"],
                shift_num=shift_info["shift_num"],
            )

        return CycleStateHistoryBatchResponse(
            success=True,
            message=f"Успешно обработано {len(results)} записей",
            results=results,
            cycles_created=cycles_created,
            cycles_completed=cycles_completed,
        )

    except Exception as e:
        # Откатываем транзакцию при любой ошибке
        await db.rollback()

        logger.error(
            "Batch state history upsert failed",
            vehicle_id=vehicle_id,
            error=str(e),
            exc_info=True,
        )

        return CycleStateHistoryBatchResponse(
            success=False,
            message=f"Ошибка: {str(e)}",
            results=[],
            cycles_created=0,
            cycles_completed=0,
        )


async def _update_existing_record(
    record_id: str,
    timestamp: datetime,
    new_state: str,
    is_end_of_cycle: bool | None,
    db: AsyncSession,
) -> CycleStateHistoryBatchResultItem:
    """Обновить существующую запись cycle_state_history.

    Сохраняет все атрибуты кроме timestamp и state.
    Также обновляет соответствующие поля в Trip при изменении статуса:
    - moving_empty -> cycle_started_at (только если старое время совпадало с cycle_started_at)
    - loading -> loading_timestamp
    - unloading -> unloading_timestamp
    - если is_end_of_cycle == true -> cycle_completed_at
    """
    from app.database.models import Trip

    query = select(CycleStateHistory).where(CycleStateHistory.id == record_id)
    result = await db.execute(query)
    record = result.scalar_one_or_none()

    if not record:
        raise ValueError(f"Запись с id={record_id} не найдена")

    # Сохраняем старое время и состояние для сравнения
    old_timestamp = record.timestamp
    old_state = record.state
    old_source = record.source

    # Проверяем, изменилось ли что-то реально
    timestamp_changed = old_timestamp != timestamp
    state_changed = old_state != new_state

    record.timestamp = timestamp
    record.state = new_state

    # Меняем source на dispatcher только если реально было изменение
    if timestamp_changed or state_changed:
        record.source = "dispatcher"

    # Обновляем поля Trip (для всех синхронизаций)
    trip_query = select(Trip).where(Trip.cycle_id == record.cycle_id)
    trip_result = await db.execute(trip_query)
    trip = trip_result.scalar_one_or_none()

    if trip:
        # Обновляем поля в зависимости от нового статуса
        if new_state == "loading":
            trip.loading_timestamp = timestamp
            trip.start_time = timestamp
            logger.debug(
                "Updated trip loading_timestamp and start_time",
                cycle_id=record.cycle_id,
                timestamp=timestamp.isoformat(),
            )
        elif new_state == "unloading":
            trip.unloading_timestamp = timestamp
            trip.end_time = timestamp
            logger.debug(
                "Updated trip unloading_timestamp and end_time",
                cycle_id=record.cycle_id,
                timestamp=timestamp.isoformat(),
            )
        # При изменении moving_empty синхронизируем cycle_started_at в Trip (через JTI)
        # ТОЛЬКО если старое время совпадало
        elif new_state == "moving_empty":
            if old_timestamp == trip.cycle_started_at:
                trip.cycle_started_at = timestamp

    # Если установлен флаг is_end_of_cycle, обновляем cycle_completed_at в Cycle/Trip
    if is_end_of_cycle:
        cycle_query = select(Cycle).where(
            Cycle.vehicle_id == record.vehicle_id,
            Cycle.cycle_completed_at == old_timestamp,
        )

        cycle_result = await db.execute(cycle_query)
        cycle_to_update = cycle_result.scalar_one_or_none()

        if cycle_to_update:
            cycle_to_update.cycle_completed_at = timestamp

    logger.debug(
        "State history record updated",
        record_id=record_id,
        old_state=old_state,
        new_state=new_state,
        old_source=old_source,
        new_source=record.source,
        timestamp_changed=timestamp_changed,
        state_changed=state_changed,
        new_timestamp=timestamp.isoformat(),
    )

    return CycleStateHistoryBatchResultItem(
        id=record.id,
        operation="updated",
        state=new_state,
        timestamp=timestamp,
        cycle_id=record.cycle_id,
        cycle_action="none",
    )


async def _create_new_record(
    vehicle_id: int,
    timestamp: datetime,
    state: str,
    cycle_id: str | None,
    cycle_action: str,
    db: AsyncSession,
) -> CycleStateHistoryBatchResultItem:
    """Создать новую запись cycle_state_history."""
    record_id = generate_uuid_vehicle_id(vehicle_id)

    record = CycleStateHistory(
        id=record_id,
        timestamp=timestamp,
        vehicle_id=vehicle_id,
        cycle_id=cycle_id,
        state=state,
        state_data={"state": state, "last_transition": timestamp.isoformat()},
        source="dispatcher",
        trigger_type="manual",
        trigger_data={"reason": "batch_upsert", "comment": "Ручное создание через API"},
    )

    db.add(record)

    logger.info(
        "State history record created",
        record_id=record_id,
        vehicle_id=vehicle_id,
        state=state,
        cycle_id=cycle_id,
        timestamp=timestamp.isoformat(),
    )

    return CycleStateHistoryBatchResultItem(
        id=record_id,
        operation="created",
        state=state,
        timestamp=timestamp,
        cycle_id=cycle_id,
        cycle_action=cycle_action,
    )


# ============================================================================
# Функции удаления записей cycle_state_history
# ============================================================================


# Маппинг состояний на поля, которые нужно очистить в Trip
STATE_TO_TRIP_FIELDS: dict[str, list[str]] = {
    "loading": ["loading_place_id", "loading_tag", "loading_timestamp"],
    "unloading": ["unloading_place_id", "unloading_tag", "unloading_timestamp"],
}

# Состояния, при которых начинается цикл
CYCLE_START_STATES = {"moving_empty", "stopped_empty", "loading"}


async def check_state_requires_cycle_deletion(
    record: CycleStateHistory,
    db: AsyncSession,
) -> tuple[bool, str | None]:
    """Проверить, приведет ли удаление записи к удалению цикла.

    Цикл должен быть удален если:
    - У записи есть cycle_id и timestamp записи совпадает с cycle_started_at этого цикла
      (т.е. статус является началом цикла)

    Args:
        record: Запись для удаления
        db: Database session

    Returns:
        Tuple[bool, Optional[str]]: (требуется удаление цикла, ID цикла)
    """
    # Если у записи нет cycle_id, то цикл удалять не нужно
    if not record.cycle_id:
        return False, None

    # Проверяем, совпадает ли timestamp статуса с cycle_started_at этого цикла
    cycle_query = (
        select(Cycle)
        .where(
            Cycle.cycle_id == record.cycle_id,
        )
        .limit(1)
    )

    cycle_result = await db.execute(cycle_query)
    cycle = cycle_result.scalar_one_or_none()

    if cycle and cycle.cycle_started_at == record.timestamp:
        return True, record.cycle_id

    return False, None


async def check_state_requires_trip_deletion(
    record: CycleStateHistory,
    db: AsyncSession,
) -> tuple[bool, str | None]:
    """Проверить, приведет ли удаление записи к удалению рейса.

    Рейс должен быть удален если:
    - Удаляемая запись - первая запись 'loading' в цикле

    Args:
        record: Запись для удаления
        db: Database session

    Returns:
        Tuple[bool, Optional[str]]: (требуется удаление рейса, ID цикла)
    """
    if not record.cycle_id or record.state != "loading":
        return False, None

    # Ищем первую запись 'loading' в этом цикле
    query = (
        select(CycleStateHistory)
        .where(
            CycleStateHistory.cycle_id == record.cycle_id,
            CycleStateHistory.state == "loading",
        )
        .order_by(CycleStateHistory.timestamp)
        .limit(1)
    )
    result = await db.execute(query)
    first_loading_record = result.scalar_one_or_none()

    # Если удаляемая запись - первая 'loading' в цикле, рейс нужно удалить
    if first_loading_record and first_loading_record.id == record.id:
        return True, record.cycle_id

    return False, None


async def get_fields_to_clear_for_state(
    state: str,
    cycle_id: str,
    db: AsyncSession,
) -> list[str]:
    """Получить список полей для очистки в Trip при удалении состояния.

    Args:
        state: Состояние которое удаляется
        cycle_id: ID цикла
        db: Database session

    Returns:
        List[str]: Список полей для очистки
    """
    fields = STATE_TO_TRIP_FIELDS.get(state, [])
    if not fields:
        return []

    query = select(Trip).where(Trip.cycle_id == cycle_id)
    result = await db.execute(query)
    trip = result.scalar_one_or_none()

    if not trip:
        return []

    return fields


async def clear_trip_fields(
    cycle_id: str,
    fields: list[str],
    db: AsyncSession,
) -> None:
    """Очистить поля в Trip при удалении связанного состояния.

    Args:
        cycle_id: ID цикла/рейса
        fields: Список полей для очистки
        db: Database session
    """
    if not fields:
        return

    query = select(Trip).where(Trip.cycle_id == cycle_id)
    result = await db.execute(query)
    trip = result.scalar_one_or_none()

    if not trip:
        return

    for field in fields:
        if hasattr(trip, field):
            setattr(trip, field, None)

    logger.info(
        "Trip fields cleared",
        cycle_id=cycle_id,
        fields=fields,
    )


async def delete_cycle_completely(
    cycle_id: str,
    db: AsyncSession,
) -> None:
    """Полностью удалить цикл и все связанные записи.

    После удаления очищает idle статусы в интервале цикла и создает no_data статус.

    Args:
        cycle_id: ID цикла
        db: Database session
    """
    from app.services.trip_state_sync_service import (
        create_no_data_status_after_cycle_deletion,
        delete_states_in_trip_interval,
    )

    # Получаем cycle_started_at, cycle_completed_at и vehicle_id перед удалением
    cycle_query = select(
        Cycle.cycle_started_at,
        Cycle.cycle_completed_at,
        Cycle.vehicle_id,
    ).where(Cycle.cycle_id == cycle_id)
    cycle_result = await db.execute(cycle_query)
    cycle_data = cycle_result.first()

    if not cycle_data:
        logger.warning(
            "Cycle not found for deletion",
            cycle_id=cycle_id,
        )
        return

    cycle_started_at, cycle_completed_at, vehicle_id = cycle_data

    await db.execute(
        delete(CycleStateHistory).where(CycleStateHistory.cycle_id == cycle_id),
    )

    await db.execute(
        delete(Trip).where(Trip.cycle_id == cycle_id),
    )

    await db.execute(
        delete(Cycle).where(Cycle.cycle_id == cycle_id),
    )

    # Очищаем все idle статусы в интервале цикла
    if cycle_started_at and vehicle_id:
        await delete_states_in_trip_interval(
            vehicle_id=vehicle_id,
            cycle_started_at=cycle_started_at,
            cycle_completed_at=cycle_completed_at,
            db=db,
        )

        # Создаем no_data статус вместо idle
        await create_no_data_status_after_cycle_deletion(
            vehicle_id=vehicle_id,
            cycle_started_at=cycle_started_at,
            db=db,
        )

    logger.info(
        "Cycle deleted completely",
        cycle_id=cycle_id,
    )


async def delete_trip_completely(
    cycle_id: str,
    db: AsyncSession,
) -> None:
    """Полностью удалить рейс (Trip) и связанные статусы state_history.

    Удаляет все CycleStateHistory записи, которые относятся к этому рейсу
    (находятся между start_time и end_time рейса).

    Args:
        cycle_id: ID цикла
        db: Database session
    """
    trip_query = select(Trip).where(Trip.cycle_id == cycle_id)
    trip_result = await db.execute(trip_query)
    trip = trip_result.scalar_one_or_none()

    if trip:
        # Удаляем статусы, которые относятся к этому рейсу
        status_conditions = [CycleStateHistory.cycle_id == cycle_id]

        if trip.start_time:
            status_conditions.append(CycleStateHistory.timestamp >= trip.start_time)
        if trip.end_time:
            status_conditions.append(CycleStateHistory.timestamp <= trip.end_time)

        if len(status_conditions) > 1:
            await db.execute(
                delete(CycleStateHistory).where(*status_conditions),
            )

        await db.execute(
            delete(Trip).where(Trip.cycle_id == cycle_id),
        )

        logger.debug(
            "Trip and related state history deleted completely",
            cycle_id=cycle_id,
            trip_start_time=trip.start_time,
            trip_end_time=trip.end_time,
        )
    else:
        logger.warning(
            "Trip not found for deletion",
            cycle_id=cycle_id,
        )


async def delete_state_history(
    record_id: str,
    confirm: bool,
    db: AsyncSession,
) -> StateHistoryDeleteResponse:
    """Удалить запись cycle_state_history.

    При удалении:
    - Для всех статусов, отличных от "no_data", при удалении меняем их на "no_data" вместо удаления
    - Статус "no_data" можно удалить полностью
    - При удалении статуса, время которого совпадает с cycle_completed_at какого-либо цикла,
      обновляем cycle_completed_at на время следующего статуса (протягиваем цикл)
    - Очищаются соответствующие поля в Trip (loading_*, unloading_*)
    - Если удаляется первая запись цикла - требуется подтверждение и удаляется весь цикл

    Args:
        record_id: ID записи для удаления
        confirm: Подтверждение удаления цикла
        db: Database session

    Returns:
        StateHistoryDeleteResponse
    """
    try:
        query = select(CycleStateHistory).where(CycleStateHistory.id == record_id)
        result = await db.execute(query)
        record = result.scalar_one_or_none()

        if not record:
            return StateHistoryDeleteResponse(
                success=False,
                message=f"Запись с id={record_id} не найдена",
            )

        vehicle_id = record.vehicle_id

        requires_cycle_deletion, cycle_id = await check_state_requires_cycle_deletion(
            record=record,
            db=db,
        )

        if not confirm:
            if requires_cycle_deletion:
                # Получаем данные цикла для отображения времени начала и завершения
                cycle_query = select(Cycle.cycle_started_at, Cycle.cycle_completed_at).where(Cycle.cycle_id == cycle_id)
                cycle_result = await db.execute(cycle_query)
                cycle_data = cycle_result.first()

                if cycle_data:
                    cycle_started_at, cycle_completed_at = cycle_data
                    started_str = format_datetime_for_message(cycle_started_at)
                    completed_str = format_datetime_for_message(cycle_completed_at)
                    message = (
                        f"Удаление этого статуса приведет к удалению цикла "
                        f"{cycle_id} ({started_str} - {completed_str}). Вы уверены?"
                    )
                else:
                    message = f"Удаление этого статуса приведет к удалению цикла {cycle_id}. Вы уверены?"
            else:
                next_timestamp = await get_next_state_timestamp(
                    vehicle_id=record.vehicle_id,
                    after_timestamp=record.timestamp,
                    db=db,
                )
                end_time = next_timestamp if next_timestamp else datetime.now(UTC)

                duration = end_time - record.timestamp
                total_seconds = int(duration.total_seconds())
                minutes = total_seconds // 60
                seconds = total_seconds % 60

                state_name = await get_status_display_name(record.state)

                start_time_str = record.timestamp.strftime("%H:%M:%S")
                end_time_str = end_time.strftime("%H:%M:%S")

                duration_str = f"{minutes} минут, {seconds} секунд" if minutes > 0 else f"{seconds} секунд"
                message = (
                    f"Вы действительно хотите удалить статус {state_name}, "
                    f"с {start_time_str} – по {end_time_str}, длительностью {duration_str}?"
                )

            return StateHistoryDeleteResponse(
                success=False,
                message=message,
                cycle_id=cycle_id if requires_cycle_deletion else None,
            )

        # Если удаляемый статус является стартом цикла - сразу применяем логику удаления цикла
        if requires_cycle_deletion:
            if cycle_id is None:
                raise RuntimeError("cycle_id is required for cycle deletion")
            await delete_cycle_completely(cycle_id, db)
            await db.commit()

            shift_info = await get_shift_info_for_timestamp(record.timestamp, record.vehicle_id)
            if shift_info:
                await _publish_history_changed_event(
                    vehicle_id=record.vehicle_id,
                    shift_date=shift_info["shift_date"],
                    shift_num=shift_info["shift_num"],
                )

            return StateHistoryDeleteResponse(
                success=True,
                message=f"Цикл {cycle_id} и все связанные записи удалены",
                deleted_record_id=record_id,
                cycle_id=cycle_id,
                cycle_deleted=True,
                trip_deleted=False,
            )

        # Для всех статусов, отличных от "no_data", при удалении меняем их на "no_data" вместо удаления
        if record.state != "no_data":
            record.state = "no_data"
            record.source = "dispatcher"
            record.state_data = {
                **(record.state_data or {}),
                "state": "no_data",
                "last_transition": record.timestamp.isoformat(),
            }
            await db.commit()

            shift_info = await get_shift_info_for_timestamp(record.timestamp, record.vehicle_id)
            if shift_info:
                await _publish_history_changed_event(
                    vehicle_id=record.vehicle_id,
                    shift_date=shift_info["shift_date"],
                    shift_num=shift_info["shift_num"],
                )

            return StateHistoryDeleteResponse(
                success=True,
                message="Статус заменён на «Нет данных»",
                deleted_record_id=record_id,
            )

        fields_cleared: list[str] = []

        # Ищем цикл, у которого cycle_completed_at совпадает с временем удаляемого статуса
        cycle_update_query = select(Cycle).where(
            Cycle.vehicle_id == vehicle_id,
            Cycle.cycle_completed_at == record.timestamp,
        )
        cycle_update_result = await db.execute(cycle_update_query)
        cycle_to_update = cycle_update_result.scalar_one_or_none()

        if cycle_to_update:
            # Проверяем, совпадает ли время удаляемого статуса с cycle_completed_at какого-либо цикла
            next_timestamp = await get_next_state_timestamp(
                vehicle_id=vehicle_id,
                after_timestamp=record.timestamp,
                db=db,
            )

            if next_timestamp:
                cycle_to_update.cycle_completed_at = next_timestamp

        await db.execute(
            delete(CycleStateHistory).where(CycleStateHistory.id == record_id),
        )
        await db.commit()

        # Публикуем событие об изменении истории
        shift_info = await get_shift_info_for_timestamp(record.timestamp, record.vehicle_id)
        if shift_info:
            await _publish_history_changed_event(
                vehicle_id=record.vehicle_id,
                shift_date=shift_info["shift_date"],
                shift_num=shift_info["shift_num"],
            )

        if record.cycle_id:
            fields_to_clear = await get_fields_to_clear_for_state(
                state=record.state,
                cycle_id=record.cycle_id,
                db=db,
            )
            if fields_to_clear:
                await clear_trip_fields(
                    cycle_id=record.cycle_id,
                    fields=fields_to_clear,
                    db=db,
                )
                fields_cleared = fields_to_clear

        logger.info(
            "State history record deleted",
            record_id=record_id,
            vehicle_id=vehicle_id,
            state=record.state,
            cycle_id=record.cycle_id,
            fields_cleared=fields_cleared,
        )
        return StateHistoryDeleteResponse(
            success=True,
            message="Запись успешно удалена",
            deleted_record_id=record_id,
            cycle_id=record.cycle_id,
            cycle_deleted=False,
            trip_deleted=False,
            fields_cleared=fields_cleared,
        )

    except Exception as e:
        await db.rollback()

        logger.error(
            "State history deletion failed",
            record_id=record_id,
            vehicle_id=vehicle_id,
            error=str(e),
            exc_info=True,
        )

        return StateHistoryDeleteResponse(
            success=False,
            message=f"Ошибка удаления: {str(e)}",
        )
