"""Сервис синхронизации статусов cycle_state_history с рейсами.

При создании/обновлении рейса через API диспетчера автоматически создаются
или обновляются записи в cycle_state_history на основе временных меток рейса.

Логика создания статусов:
1. cycle_started_at -> moving_empty
2. loading_timestamp -> loading
3. loading_timestamp + 30 сек -> moving_loaded
4. unloading_timestamp - 10 сек -> stopped_loaded
5. unloading_timestamp -> unloading
6. cycle_completed_at -> idle
"""

from datetime import datetime, timedelta
from typing import Any, cast

import httpx
from loguru import logger
from sqlalchemy import CursorResult, and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.base import generate_uuid_vehicle_id
from app.database.models import Cycle, CycleStateHistory, Trip
from app.services.state_history_service import (
    _publish_history_changed_event,
    get_shift_info_for_timestamp,
)

# Интервал после loading до moving_loaded (30 секунд)
LOADING_TO_MOVING_INTERVAL_SECONDS = 30

# Интервал до unloading для stopped_loaded (10 секунд)
STOPPED_LOADED_BEFORE_UNLOADING_SECONDS = 10


async def get_shift_time_range(
    shift_date: str,
    shift_num: int,
) -> dict[str, datetime] | None:
    """Получить временной диапазон смены через enterprise-service.

    Args:
        shift_date: Дата смены в формате ISO (YYYY-MM-DD)
        shift_num: Номер смены

    Returns:
        Словарь с 'start_time' и 'end_time' или None
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.enterprise_service_url}/api/shift-service/get-shift-time-range",
                params={
                    "shift_date": shift_date,
                    "shift_number": shift_num,
                },
                timeout=5.0,
            )

            if response.status_code == 200:
                data = response.json()
                # Парсим datetime из ISO строк
                start_time = datetime.fromisoformat(data["start_time"].replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(data["end_time"].replace("Z", "+00:00"))
                return {
                    "start_time": start_time,
                    "end_time": end_time,
                }
            else:
                logger.warning(
                    "Failed to get shift time range from enterprise-service",
                    shift_date=shift_date,
                    shift_num=shift_num,
                    status_code=response.status_code,
                    response_text=response.text,
                )
                return None
    except Exception as e:
        logger.error(
            "Error getting shift time range from enterprise-service",
            shift_date=shift_date,
            shift_num=shift_num,
            error=str(e),
        )
        return None


async def delete_states_in_trip_interval(
    vehicle_id: int,
    cycle_started_at: datetime | None,
    cycle_completed_at: datetime | None,
    db: AsyncSession,
) -> int:
    """Удалить все статусы в интервале рейса.

    При создании рейса все статусы в его интервале должны быть удалены,
    так как теперь в этом интервале есть рейс.

    Args:
        vehicle_id: ID транспортного средства
        cycle_started_at: Время начала цикла
        cycle_completed_at: Время завершения цикла
        db: Database session

    Returns:
        Количество удаленных записей
    """
    if not cycle_started_at:
        logger.debug("No cycle_started_at, skipping idle deletion")
        return 0

    # Строим условия для поиска idle статусов в интервале рейса
    conditions = [
        CycleStateHistory.vehicle_id == vehicle_id,
        CycleStateHistory.timestamp >= cycle_started_at,
    ]

    # Если есть время завершения - ограничиваем интервал
    if cycle_completed_at:
        conditions.append(CycleStateHistory.timestamp < cycle_completed_at)

    # Находим idle статусы для удаления
    select_query = select(CycleStateHistory).where(and_(*conditions))
    result = await db.execute(select_query)
    records = result.scalars().all()

    if not records:
        logger.debug(
            "No idle states found in trip interval",
            vehicle_id=vehicle_id,
            cycle_started_at=cycle_started_at.isoformat(),
            cycle_completed_at=cycle_completed_at.isoformat() if cycle_completed_at else None,
        )
        return 0

    # Удаляем найденные idle статусы
    deleted_count = len(records)
    for record in records:
        logger.debug(
            "Deleting idle state in trip interval",
            record_id=record.id,
            timestamp=record.timestamp.isoformat(),
            vehicle_id=vehicle_id,
        )
        await db.delete(record)

    await db.flush()

    logger.info(
        "Deleted idle states in trip interval",
        vehicle_id=vehicle_id,
        deleted_count=deleted_count,
        cycle_started_at=cycle_started_at.isoformat(),
        cycle_completed_at=cycle_completed_at.isoformat() if cycle_completed_at else None,
    )

    return deleted_count


async def create_trip_state_history(
    trip: Trip,
    db: AsyncSession,
) -> list[CycleStateHistory]:
    """Создать записи cycle_state_history для НОВОГО рейса (POST запрос).

    Создает все статусы на основе временных меток рейса.
    Удаляет все статусы idle в интервале рейса.

    Args:
        trip: Объект рейса с заполненными временными метками
        db: Database session

    Returns:
        Список созданных записей CycleStateHistory
    """
    cycle_id = trip.cycle_id
    vehicle_id = trip.vehicle_id

    logger.info(
        "Creating state history for new trip",
        cycle_id=cycle_id,
        vehicle_id=vehicle_id,
        loading_timestamp=trip.loading_timestamp,
        unloading_timestamp=trip.unloading_timestamp,
    )

    # Удаляем все статусы idle в интервале рейса
    await delete_states_in_trip_interval(
        vehicle_id=vehicle_id,
        cycle_started_at=trip.cycle_started_at,
        cycle_completed_at=trip.cycle_completed_at,
        db=db,
    )

    # Собираем статусы для создания
    states_to_create: list[dict[str, Any]] = []

    # 1. Начало цикла - moving_empty
    cycle_started_at = trip.cycle_started_at
    if cycle_started_at:
        states_to_create.append(
            {
                "state": "moving_empty",
                "timestamp": cycle_started_at,
                "place_id": trip.from_place_id or trip.loading_place_id,
            },
        )

    # 2. Погрузка - loading в момент loading_timestamp
    loading_timestamp = trip.loading_timestamp
    if loading_timestamp:
        states_to_create.append(
            {
                "state": "loading",
                "timestamp": loading_timestamp,
                "place_id": trip.loading_place_id,
            },
        )

        # moving_loaded через 30 секунд после loading_timestamp
        moving_loaded_time: datetime | None = loading_timestamp + timedelta(seconds=LOADING_TO_MOVING_INTERVAL_SECONDS)
        states_to_create.append(
            {
                "state": "moving_loaded",
                "timestamp": moving_loaded_time,
                "place_id": trip.loading_place_id,
            },
        )

    # 3. Разгрузка
    unloading_timestamp = trip.unloading_timestamp
    if unloading_timestamp:
        # stopped_loaded за 10 секунд до unloading_timestamp
        stopped_loaded_time = unloading_timestamp - timedelta(seconds=STOPPED_LOADED_BEFORE_UNLOADING_SECONDS)

        # Проверяем, что stopped_loaded_time > moving_loaded_time (если есть)
        moving_loaded_time = (
            loading_timestamp + timedelta(seconds=LOADING_TO_MOVING_INTERVAL_SECONDS) if loading_timestamp else None
        )
        if moving_loaded_time and stopped_loaded_time <= moving_loaded_time:
            stopped_loaded_time = moving_loaded_time + timedelta(
                seconds=(unloading_timestamp - moving_loaded_time).total_seconds() / 2,
            )

        states_to_create.append(
            {
                "state": "stopped_loaded",
                "timestamp": stopped_loaded_time,
                "place_id": trip.unloading_place_id,
            },
        )

        # unloading в момент unloading_timestamp
        states_to_create.append(
            {
                "state": "unloading",
                "timestamp": unloading_timestamp,
                "place_id": trip.unloading_place_id,
            },
        )

    # 4. Завершение цикла - idle
    cycle_completed_at = trip.cycle_completed_at
    if cycle_completed_at:
        states_to_create.append(
            {
                "state": "idle",
                "timestamp": cycle_completed_at,
                "place_id": trip.to_place_id or trip.unloading_place_id,
            },
        )

    # Сортируем по времени
    states_to_create.sort(key=lambda x: x["timestamp"])

    # Создаем записи
    created_records: list[CycleStateHistory] = []

    for state_info in states_to_create:
        record_id = generate_uuid_vehicle_id(vehicle_id)
        record_cycle_id = None if state_info["state"] == "idle" else cycle_id

        record = CycleStateHistory(
            id=record_id,
            timestamp=state_info["timestamp"],
            vehicle_id=vehicle_id,
            cycle_id=record_cycle_id,
            state=state_info["state"],
            state_data={
                "state": state_info["state"],
                "last_transition": state_info["timestamp"].isoformat(),
                "cycle_id": record_cycle_id,
            },
            place_id=state_info.get("place_id"),
            source="dispatcher",
            task_id=trip.task_id,
            trigger_type="manual",
            trigger_data={
                "reason": "trip_create",
                "comment": "Создано при создании рейса",
            },
        )

        db.add(record)
        created_records.append(record)

        logger.debug(
            "Created state history record",
            record_id=record_id,
            state=state_info["state"],
            timestamp=state_info["timestamp"].isoformat(),
            cycle_id=record_cycle_id,
        )

    await db.flush()

    logger.info(
        "State history created for new trip",
        cycle_id=cycle_id,
        vehicle_id=vehicle_id,
        records_created=len(created_records),
    )

    return created_records


async def update_trip_state_history(
    trip: Trip,
    db: AsyncSession,
    old_cycle_completed_at: datetime | None = None,
    old_cycle_started_at: datetime | None = None,
) -> int:
    """Обновить записи cycle_state_history для СУЩЕСТВУЮЩЕГО рейса (PUT запрос).

    Обновляет время существующих статусов на основе временных меток рейса.
    Ищет среди ВСЕХ статусов (и dispatcher, и system).
    После обновления статус становится source="dispatcher".

    Для moving_empty обновляет только тот, который является началом цикла (первый по времени).

    Args:
        trip: Объект рейса с заполненными временными метками
        db: Database session
        old_cycle_completed_at: Предыдущее время завершения цикла (опционально)
        old_cycle_started_at: Предыдущее время начала цикла (опционально)

    Returns:
        Количество обновленных записей
    """
    cycle_id = trip.cycle_id
    vehicle_id = trip.vehicle_id

    # Получаем ВСЕ существующие статусы для этого цикла (любой source)
    existing_query = (
        select(CycleStateHistory).where(CycleStateHistory.cycle_id == cycle_id).order_by(CycleStateHistory.timestamp)
    )
    result = await db.execute(existing_query)
    existing_records = list(result.scalars().all())

    # Находим конкретные статусы для обновления
    # Для moving_empty - берем ПЕРВЫЙ по времени (это начало цикла)
    # Для loading, unloading - берем ПЕРВЫЙ по времени
    state_records = _find_trip_state_records(existing_records, trip)

    updated_count = 0

    # Маппинг полей рейса на статусы и их времена
    state_mappings = _build_state_mappings(trip)

    for state_name, state_info in state_mappings.items():
        new_timestamp = state_info["timestamp"]
        place_id = state_info.get("place_id")

        if state_name in state_records:
            # Статус существует - обновляем время только если оно изменилось
            record = state_records[state_name]
            if record.timestamp != new_timestamp or record.place_id != place_id:
                record.timestamp = new_timestamp
                record.place_id = place_id
                record.source = "dispatcher"  # При реальном изменении статус становится dispatcher
                record.state_data = {
                    "state": state_name,
                    "last_transition": new_timestamp.isoformat(),
                    "cycle_id": cycle_id,
                }
        else:
            # Статус не существует - создаем новый
            record_id = generate_uuid_vehicle_id(vehicle_id)
            new_record = CycleStateHistory(
                id=record_id,
                timestamp=new_timestamp,
                vehicle_id=vehicle_id,
                cycle_id=cycle_id,
                state=state_name,
                state_data={
                    "state": state_name,
                    "last_transition": new_timestamp.isoformat(),
                    "cycle_id": cycle_id,
                },
                place_id=place_id,
                source="dispatcher",
                task_id=trip.task_id,
                trigger_type="manual",
                trigger_data={
                    "reason": "trip_update",
                    "comment": "Создано при обновлении рейса (поле ранее было пустым)",
                },
            )
            db.add(new_record)

    # Если cycle_completed_at изменился, обновляем соответствующий статус по старому времени
    if old_cycle_completed_at and trip.cycle_completed_at and old_cycle_completed_at != trip.cycle_completed_at:
        old_status_query = (
            select(CycleStateHistory)
            .where(
                and_(
                    CycleStateHistory.vehicle_id == vehicle_id,
                    CycleStateHistory.timestamp == old_cycle_completed_at,
                ),
            )
            .limit(1)
        )
        old_status_result = await db.execute(old_status_query)
        old_status = old_status_result.scalar_one_or_none()

        if old_status:
            old_status.timestamp = trip.cycle_completed_at
            old_status.source = "dispatcher"

        # Ищем следующий цикл, который начинается в то же время (cycle_started_at == old_cycle_completed_at)
        next_cycle_query = (
            select(Cycle)
            .where(
                and_(
                    Cycle.vehicle_id == vehicle_id,
                    Cycle.cycle_started_at == old_cycle_completed_at,
                    Cycle.cycle_id != cycle_id,  # Исключаем текущий цикл
                ),
            )
            .limit(1)
        )
        next_cycle_result = await db.execute(next_cycle_query)
        next_cycle = next_cycle_result.scalar_one_or_none()

        if next_cycle:
            next_cycle.cycle_started_at = trip.cycle_completed_at

    # Если cycle_started_at изменился, обновляем соответствующий статус по старому времени
    if old_cycle_started_at and trip.cycle_started_at and old_cycle_started_at != trip.cycle_started_at:
        old_start_status_query = (
            select(CycleStateHistory)
            .where(
                and_(
                    CycleStateHistory.vehicle_id == vehicle_id,
                    CycleStateHistory.timestamp == old_cycle_started_at,
                ),
            )
            .limit(1)
        )
        old_start_status_result = await db.execute(old_start_status_query)
        old_start_status = old_start_status_result.scalar_one_or_none()

        if old_start_status:
            old_start_status.timestamp = trip.cycle_started_at
            old_start_status.source = "dispatcher"

        # Обновляем окончание предыдущего цикла, если его cycle_completed_at совпадал со старым началом текущего
        prev_cycle_query = (
            select(Cycle)
            .where(
                and_(
                    Cycle.vehicle_id == vehicle_id,
                    Cycle.cycle_completed_at == old_cycle_started_at,
                    Cycle.cycle_id != cycle_id,
                ),
            )
            .limit(1)
        )
        prev_cycle_result = await db.execute(prev_cycle_query)
        prev_cycle = prev_cycle_result.scalar_one_or_none()

        if prev_cycle:
            prev_cycle.cycle_completed_at = trip.cycle_started_at

    await db.flush()

    logger.info(
        "State history updated for trip",
        cycle_id=cycle_id,
        vehicle_id=vehicle_id,
        updated_count=updated_count,
    )

    return updated_count


def _find_trip_state_records(
    records: list[CycleStateHistory],
    trip: Trip,
) -> dict[str, CycleStateHistory]:
    """Найти конкретные статусы, соответствующие полям рейса.

    Логика поиска:
    - moving_empty: ПЕРВЫЙ по времени (это начало цикла)
    - loading: ПЕРВЫЙ loading по времени
    - unloading: ПЕРВЫЙ unloading по времени

    Args:
        records: Список всех статусов цикла (отсортированы по времени)
        trip: Объект рейса

    Returns:
        Словарь {state_name: CycleStateHistory}
    """
    result: dict[str, CycleStateHistory] = {}

    # Группируем статусы по типу
    by_state: dict[str, list[CycleStateHistory]] = {}
    for record in records:
        if record.state not in by_state:
            by_state[record.state] = []
        by_state[record.state].append(record)

    # moving_empty: первый по времени
    if "moving_empty" in by_state and by_state["moving_empty"]:
        result["moving_empty"] = by_state["moving_empty"][0]

    # loading: первый по времени
    if "loading" in by_state and by_state["loading"]:
        result["loading"] = by_state["loading"][0]

    # unloading: первый по времени
    if "unloading" in by_state and by_state["unloading"]:
        result["unloading"] = by_state["unloading"][0]

    return result


async def check_trip_overlap(
    vehicle_id: int,
    cycle_started_at: datetime,
    cycle_completed_at: datetime | None,
    cycle_id: str | None,
    db: AsyncSession,
) -> dict[str, Any] | None:
    """Проверить пересечения нового рейса с существующими рейсами на том же транспортном средстве.

    Проверка выполняется только в рамках той же смены, к которой относится cycle_started_at.
    Возвращает данные о конфликтующем рейсе, если есть пересечение, иначе None.

    Args:
        vehicle_id: ID транспортного средства
        cycle_started_at: Время начала нового цикла
        cycle_completed_at: Время завершения нового цикла (может быть None)
        cycle_id: ID цикла (исключить из проверки, если обновляем существующий)
        db: Database session

    Returns:
        Dict с данными конфликтующего рейса или None
    """
    logger.info(
        "Checking trip overlap",
        vehicle_id=vehicle_id,
        cycle_started_at=cycle_started_at.isoformat(),
        cycle_completed_at=cycle_completed_at.isoformat() if cycle_completed_at else None,
        cycle_id=cycle_id,
    )

    # Определяем смену для cycle_started_at
    shift_info = await get_shift_info_for_timestamp(cycle_started_at, vehicle_id)

    shift_start: datetime | None = None
    shift_end: datetime | None = None

    if shift_info:
        # Получаем границы смены
        shift_time_range = await get_shift_time_range(
            shift_date=shift_info["shift_date"],
            shift_num=shift_info["shift_num"],
        )
        if shift_time_range:
            shift_start = shift_time_range["start_time"]
            shift_end = shift_time_range["end_time"]

    # Строим условие для поиска пересечений
    conditions = []

    # Основное условие: тот же vehicle_id
    conditions.append(Trip.vehicle_id == vehicle_id)

    # Исключаем текущий цикл при обновлении
    if cycle_id:
        conditions.append(Trip.cycle_id != cycle_id)

    # Ограничиваем поиск рамками смены (если границы определены)
    if shift_start and shift_end:
        conditions.append(Trip.cycle_started_at >= shift_start)
        conditions.append(Trip.cycle_started_at < shift_end)

    # Условие пересечения: новый цикл пересекается с существующим
    # Пересечение если:
    # 1. Новый цикл начинается внутри существующего
    # 2. Новый цикл заканчивается внутри существующего
    # 3. Новый цикл полностью покрывает существующий

    overlap_conditions = []

    if cycle_completed_at:
        # Оба времени заданы - проверяем стандартное пересечение интервалов
        # Новый [A,B] пересекается с существующим [C,D] если:
        # A < D AND B > C (интервалы накладываются)
        overlap_conditions.append(
            and_(
                cycle_started_at < Trip.cycle_completed_at,  # Новый начинается до завершения существующего
                cycle_completed_at > Trip.cycle_started_at,  # Новый заканчивается после начала существующего
            ),
        )
        # Специально обрабатываем незавершенные рейсы (cycle_completed_at = None)
        # Новый рейс пересекается с незавершенным, если начинается после начала незавершенного
        overlap_conditions.append(
            and_(
                cycle_started_at >= Trip.cycle_started_at,  # Новый начинается после или одновременно с незавершенным
                Trip.cycle_completed_at.is_(None),  # Существующий рейс не завершен
            ),
        )
    else:
        # Только начало задано - проверяем пересечение с бесконечным интервалом
        # Новый рейс (с бесконечным концом) пересекается если начинается до завершения существующего
        overlap_conditions.append(
            or_(
                cycle_started_at < Trip.cycle_completed_at,  # Начинается до завершения существующего
                Trip.cycle_completed_at.is_(None),  # Существующий рейс не завершен
            ),
        )

    conditions.append(or_(*overlap_conditions))

    query = (
        select(Trip.cycle_id, Trip.cycle_started_at, Trip.cycle_completed_at)
        .where(and_(*conditions))
        .limit(1)  # Нам нужен только первый конфликт
    )

    logger.debug("Overlap query", query=str(query))

    try:
        result = await db.execute(query)
        conflicting_trip = result.first()
    except Exception as query_error:
        logger.error("Database query error in check_trip_overlap", error=str(query_error), exc_info=True)
        raise

    # Дополнительное логирование для отладки
    logger.debug(
        "Overlap query executed",
        vehicle_id=vehicle_id,
        cycle_started_at=cycle_started_at.isoformat(),
        cycle_completed_at=cycle_completed_at.isoformat() if cycle_completed_at else None,
        cycle_id=cycle_id,
    )

    logger.info(
        "Overlap check result",
        found_conflict=conflicting_trip is not None,
        conflicting_trip_id=conflicting_trip.cycle_id if conflicting_trip else None,
        conflicting_started=conflicting_trip.cycle_started_at.isoformat()
        if conflicting_trip and conflicting_trip.cycle_started_at
        else None,
        conflicting_completed=conflicting_trip.cycle_completed_at.isoformat()
        if conflicting_trip and conflicting_trip.cycle_completed_at
        else None,
        new_started=cycle_started_at.isoformat(),
        new_completed=cycle_completed_at.isoformat() if cycle_completed_at else None,
    )

    if conflicting_trip:
        return {
            "cycle_id": conflicting_trip.cycle_id,
            "cycle_started_at": conflicting_trip.cycle_started_at,
            "cycle_completed_at": conflicting_trip.cycle_completed_at,
        }

    return None


async def create_no_data_status_after_cycle_deletion(
    vehicle_id: int,
    cycle_started_at: datetime,
    db: AsyncSession,
) -> CycleStateHistory:
    """Создать статус "no_data" (Нет данных) после удаления цикла.

    Статус no_data используется для заполнения пустоты на месте удаленного рейса,
    чтобы показать, что в этот период данные отсутствуют.

    Args:
        vehicle_id: ID транспортного средства
        cycle_started_at: Время начала удаленного цикла (используется как timestamp для no_data)
        db: Database session

    Returns:
        Созданная запись CycleStateHistory
    """
    from app.database.base import generate_uuid_vehicle_id
    from app.database.models import CycleStateHistory

    record_id = generate_uuid_vehicle_id(vehicle_id)

    no_data_record = CycleStateHistory(
        id=record_id,
        timestamp=cycle_started_at,  # Используем время начала цикла
        vehicle_id=vehicle_id,
        cycle_id=None,  # Нет привязки к циклу
        state="no_data",
        state_data={
            "state": "no_data",
            "last_transition": cycle_started_at.isoformat(),
        },
        place_id=None,
        source="dispatcher",
        task_id=None,
        trigger_type="manual",
        trigger_data={
            "reason": "cycle_deletion",
            "comment": "Автоматически создано при удалении цикла, timestamp=cycle_started_at",
        },
    )

    db.add(no_data_record)
    await db.flush()

    logger.info(
        "Created no_data status after cycle deletion",
        vehicle_id=vehicle_id,
        no_data_record_id=record_id,
        timestamp=cycle_started_at.isoformat(),
    )

    return no_data_record


def _build_state_mappings(trip: Trip) -> dict[str, dict[str, Any]]:
    """Построить маппинг статусов на основе временных меток рейса.

    Returns:
        Словарь {state_name: {"timestamp": datetime, "place_id": int}}
    """
    mappings: dict[str, dict[str, Any]] = {}

    # moving_empty -> cycle_started_at
    if trip.cycle_started_at:
        mappings["moving_empty"] = {
            "timestamp": trip.cycle_started_at,
        }

    # loading -> loading_timestamp
    if trip.loading_timestamp:
        mappings["loading"] = {
            "timestamp": trip.loading_timestamp,
            "place_id": trip.loading_place_id,
        }

    # unloading -> unloading_timestamp
    if trip.unloading_timestamp:
        mappings["unloading"] = {
            "timestamp": trip.unloading_timestamp,
            "place_id": trip.unloading_place_id,
        }

    return mappings


async def delete_trip_state_history(
    cycle_id: str,
    db: AsyncSession,
) -> int:
    """Удалить все записи cycle_state_history для рейса.

    Args:
        cycle_id: ID цикла/рейса
        db: Database session

    Returns:
        Количество удаленных записей
    """
    result = cast(
        CursorResult[Any],
        await db.execute(
            delete(CycleStateHistory).where(CycleStateHistory.cycle_id == cycle_id),
        ),
    )

    deleted_count = result.rowcount

    logger.info(
        "Deleted state history for trip",
        cycle_id=cycle_id,
        deleted_count=deleted_count,
    )

    return deleted_count


async def publish_trip_history_changed_event(
    trip: Trip,
) -> None:
    """Публикация события об изменении истории для рейса.

    Определяет смену по времени рейса и публикует событие history_changed.

    Args:
        trip: Объект рейса
    """
    # Определяем время для получения информации о смене
    timestamp = trip.loading_timestamp or trip.cycle_started_at or trip.start_time

    if not timestamp:
        logger.warning(
            "Cannot publish history_changed event - no timestamp",
            cycle_id=trip.cycle_id,
        )
        return

    # Получаем информацию о смене
    shift_info = await get_shift_info_for_timestamp(timestamp, trip.vehicle_id)

    if shift_info:
        await _publish_history_changed_event(
            vehicle_id=trip.vehicle_id,
            shift_date=shift_info["shift_date"],
            shift_num=shift_info["shift_num"],
        )

        logger.info(
            "Published history_changed event for trip",
            cycle_id=trip.cycle_id,
            vehicle_id=trip.vehicle_id,
            shift_date=shift_info["shift_date"],
            shift_num=shift_info["shift_num"],
        )
    else:
        logger.warning(
            "Could not get shift info for trip",
            cycle_id=trip.cycle_id,
            vehicle_id=trip.vehicle_id,
            timestamp=timestamp.isoformat(),
        )
