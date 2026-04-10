"""Trip Manager - управление жизненным циклом рейсов.

Основные функции:
- create_trip() - создание рейса с определением типа (planned/unplanned)
- complete_trip() - завершение рейса с проверкой точки разгрузки
- Связь с заданиями (UPDATE tasks при создании/завершении)
- Сохранение tag_history из Redis Stream в PostgreSQL
- Публикация событий в MQTT (trip_started, trip_completed)
- Инструменты для работы с Trip.cycle_num (construct_trip_cycle_num_subquery и bulk_update_trips_cycle_num)
"""

import json
from datetime import UTC, datetime
from typing import Any, cast

from loguru import logger
from sqlalchemy import ScalarSelect, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import redis_client
from app.database.base import generate_uuid_vehicle_id
from app.database.models import Cycle, CycleTagHistory, PlaceRemainingHistory, RouteTask, Trip
from app.enums.route_tasks import TripStatusRouteEnum
from app.services.enterprise_client import enterprise_client
from app.services.place_remaining import place_remaining_service
from app.services.trip_event_publisher import publish_trip_event
from app.utils import truncate_datetime_to_seconds


async def create_trip(
    vehicle_id: str,
    place_id: int,
    tag: str | int | None,
    active_task_id: str | None = None,
    cycle_id: str | None = None,
    loading_timestamp: datetime | None = None,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """Создать новый рейс внутри цикла.

    Рейс создается при переходе в moving_loaded и всегда привязан к циклу.

    Определяет тип рейса на основе наличия активного задания:
    - planned: если есть активное задание и загрузка началась в place_a_id
    - unplanned: во всех остальных случаях

    Args:
        vehicle_id: ID транспорта
        place_id: ID места начала рейса (place.id из graph-service)
        tag: Метка локации
        active_task_id: ID активного задания (опционально)
        cycle_id: ID цикла, к которому привязан рейс
        loading_timestamp: Время начала погрузки (из state_data при переходе в loading)
        db: Database session

    Returns:
        dict: {"cycle_id": str, "trip_type": str, "task_id": Optional[str]}
    """
    # cycle_id НЕ генерируем! Он передается как параметр - Trip создается ВНУТРИ существующего Cycle
    now = cast(datetime, truncate_datetime_to_seconds(datetime.now(UTC)))

    tag_str = str(tag) if tag is not None else None

    # Используем переданный loading_timestamp или now как fallback
    if not loading_timestamp:
        loading_timestamp = now

    # Определить тип рейса
    trip_type = "unplanned"
    task_id = None
    shift_id = None

    if active_task_id and db:
        # Проверить, начинается ли рейс в плановой точке
        query = select(RouteTask).where(RouteTask.id == active_task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()

        if task and task.place_a_id == place_id:
            # Плановый рейс - начинается в правильной точке
            trip_type = "planned"
            task_id = task.id
            shift_id = task.shift_task_id if task.shift_task_id else None

            # Обновить задание - статус active
            task.status = TripStatusRouteEnum.ACTIVE
            # Связь через trip.task_id, не нужно task.cycle_id
            await db.commit()

            logger.info(
                "RouteTask activated for trip",
                vehicle_id=vehicle_id,
                task_id=task_id,
                cycle_id=cycle_id,
            )

    # Преобразовать существующий Cycle в Trip через JTI
    if db:
        # cycle_id ОБЯЗАТЕЛЕН - рейс создается ВНУТРИ цикла
        if not cycle_id:
            logger.error("create_trip called without cycle_id - trip must be inside a cycle!", vehicle_id=vehicle_id)
            raise ValueError(f"cycle_id is required to create a trip for vehicle {vehicle_id}")

        # Найти существующий Cycle
        from app.database.models import Cycle

        cycle_query = select(Cycle).where(Cycle.cycle_id == cycle_id)
        cycle_result = await db.execute(cycle_query)
        cycle = cycle_result.scalar_one_or_none()

        if cycle:
            # JTI: Создаем запись в Trip, связанную с Cycle
            from sqlalchemy import insert, update

            # Обновляем Cycle — в БД task_id и shift_id строки (VARCHAR)
            cycle.task_id = task_id if task_id else None
            cycle.shift_id = shift_id if shift_id else None
            await db.flush()  # Сохраняем изменения Cycle

            # start_time = now (время перехода в moving_loaded, конец погрузки)
            # loading_timestamp = время перехода в loading (начало погрузки)
            cycle_num_subquery = await construct_trip_cycle_num_subquery(cycle.vehicle_id, now)
            cycle_num = 1 if cycle_num_subquery is None else cycle_num_subquery
            await db.execute(
                insert(Trip).values(
                    cycle_id=cycle_id,
                    trip_type=trip_type,
                    start_time=now,
                    loading_place_id=place_id,
                    loading_tag=tag_str,
                    loading_timestamp=loading_timestamp,
                    cycle_num=cycle_num,
                ),
            )

            # UPDATE entity_type в таблице cycles для JTI polymorphism
            await db.execute(
                update(Cycle).where(Cycle.cycle_id == cycle_id).values(entity_type="trip"),
            )

            await db.commit()

            logger.info("Cycle converted to Trip via JTI", cycle_id=cycle_id, trip_type=trip_type)
        else:
            # Если цикла нет, это ошибка - Trip должен создаваться ТОЛЬКО внутри Cycle
            logger.error("Cycle not found, cannot create Trip without Cycle!", cycle_id=cycle_id)
            raise ValueError(f"Cannot create Trip without existing Cycle: {cycle_id}")

    # Сохранить в Redis active_trip
    trip_data = {
        "cycle_id": cycle_id,
        "vehicle_id": vehicle_id,
        "trip_type": trip_type,
        "status": "active",
        "task_id": task_id if task_id else None,
        "shift_id": shift_id if shift_id else None,
        "start_time": loading_timestamp.isoformat(),
        "loading_place_id": place_id,
        "loading_tag": tag_str,
    }
    await redis_client.set_active_trip(vehicle_id, trip_data)

    # Публикуем обновление в Redis Pub/Sub для фронтенда (создание trip)
    try:
        trip_update = {
            "cycle_id": cycle_id,
            "trip_type": trip_type,
            "status": "active",
            "loading_place_id": place_id,
            "loading_timestamp": loading_timestamp.isoformat(),
            "event_type": "trip_started",
        }
        channel = f"trip-service:vehicle:{vehicle_id}:events"
        payload = json.dumps(trip_update)
        if redis_client.redis is not None:
            await redis_client.redis.publish(channel, payload)
        logger.info("Trip update published to Redis", cycle_id=cycle_id, trip_type=trip_type, status="active")
    except Exception as e:
        logger.error("Failed to publish trip update to Redis", error=str(e), exc_info=True)

    logger.info(
        "Trip created",
        vehicle_id=vehicle_id,
        cycle_id=cycle_id,
        trip_type=trip_type,
        task_id=task_id,
        place_id=place_id,
    )

    # Публикуем событие trip_started в MQTT
    await publish_trip_event(
        event_type="trip_started",
        cycle_id=cycle_id,
        server_trip_id=task_id,
        trip_type=trip_type,
        vehicle_id=vehicle_id,
        place_id=place_id,
        state="loading",
        shift_id=shift_id,
        tag=tag_str,
    )

    return {
        "cycle_id": cycle_id,
        "trip_type": trip_type,
        "task_id": task_id,
    }


async def complete_trip(
    vehicle_id: int,
    cycle_id: str,
    place_id: int,
    tag: str,
    db: AsyncSession | None = None,
    end_time: datetime | None = None,
    unloading_timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Завершить рейс.

    Проверяет место разгрузки:
    - Если разгрузка в плановом месте place_b_id → trip остается "planned"
    - Если разгрузка НЕ в плановом месте → изменить на "unplanned" и разорвать связь с заданием

    Сохраняет tag_history из Redis Stream в PostgreSQL.
    Вычисляет и сохраняет аналитику.

    Args:
        vehicle_id: ID транспорта
        cycle_id: ID цикла/рейса (Trip ID = Cycle ID)
        place_id: ID места завершения (place.id из graph-service)
        tag: Метка локации
        db: Database session
        end_time: Время завершения рейса (опционально)
        unloading_timestamp: Время начала разгрузки (из state_data при переходе в unloading)

    Returns:
        dict с результатом: {"success": bool, "message": str, "next_task_id": Optional[str]}
    """
    if not db:
        return {"success": False, "message": "Database session required"}

    # Используем переданное время завершения или текущее время
    now = end_time if end_time else cast(datetime, truncate_datetime_to_seconds(datetime.now(UTC)))

    # Найти рейс в PostgreSQL (Trip ID = Cycle ID)
    query = select(Trip).where(Trip.cycle_id == cycle_id)
    result = await db.execute(query)
    trip = result.scalar_one_or_none()

    if not trip:
        logger.error(
            "Trip not found",
            vehicle_id=vehicle_id,
            cycle_id=cycle_id,
        )
        return {"success": False, "message": "Trip not found"}

    # Проверить тип рейса и точку разгрузки
    task_completed = False
    task_cancelled = False
    next_task_id = None  # Инициализируем переменную
    original_trip_type = trip.trip_type

    if trip.trip_type == "planned" and trip.task_id:
        # Найти связанное задание через trip.task_id
        task_query = select(RouteTask).where(
            RouteTask.id == trip.task_id,
            RouteTask.status == TripStatusRouteEnum.ACTIVE,
        )
        task_result = await db.execute(task_query)
        task = task_result.scalar_one_or_none()

        if task:
            if task.place_b_id == place_id:
                # Разгрузка в правильной точке - рейс остается плановым
                task.status = TripStatusRouteEnum.COMPLETED
                task.actual_trips_count = (task.actual_trips_count or 0) + 1
                task_completed = True

                logger.info(
                    "RouteTask completed successfully",
                    vehicle_id=vehicle_id,
                    task_id=task.id,
                    cycle_id=cycle_id,
                    actual_trips_count=task.actual_trips_count,
                )
            else:
                # Разгрузка НЕ в правильной точке - меняем на внеплановый
                trip.trip_type = "unplanned"
                task.status = TripStatusRouteEnum.COMPLETED
                # Связь разрывается автоматически через trip.trip_type = "unplanned"
                task_cancelled = True

                logger.warning(
                    "Trip changed to unplanned - wrong unloading place",
                    vehicle_id=vehicle_id,
                    task_id=task.id,
                    cycle_id=cycle_id,
                    expected_place=task.place_b_id,
                    actual_place=place_id,
                )

    # Используем переданный unloading_timestamp или now как fallback
    if not unloading_timestamp:
        unloading_timestamp = now

    # Обновить рейс
    # end_time = now (время перехода в moving_empty, конец разгрузки)
    # unloading_timestamp = время перехода в unloading (начало разгрузки)
    trip.end_time = now
    trip.unloading_place_id = place_id
    trip.unloading_tag = str(tag) if tag is not None else None
    trip.unloading_timestamp = unloading_timestamp
    trip.cycle_status = TripStatusRouteEnum.COMPLETED.value

    await db.commit()

    # Публикуем обновление статуса trip в Redis для фронтенда
    trip_update = {
        "cycle_id": cycle_id,
        "status": trip.cycle_status,
        "trip_type": trip.trip_type,
        "unloading_place_id": place_id,
        "unloading_timestamp": unloading_timestamp.isoformat(),
        "event_type": "trip_completed",
    }
    channel = f"trip-service:vehicle:{vehicle_id}:events"
    if redis_client.redis is not None:
        await redis_client.redis.publish(channel, json.dumps(trip_update))
    logger.info(f"Trip update published to Redis: {cycle_id} status={trip.cycle_status}")

    # Сохранить tag_history из Redis Stream в PostgreSQL
    try:
        await _save_tag_history_from_redis(
            vehicle_id=vehicle_id,
            cycle_id=cycle_id,
            db=db,
        )
    except Exception as e:
        logger.warning(
            "Failed to save tag history from Redis",
            vehicle_id=vehicle_id,
            cycle_id=cycle_id,
            error=str(e),
        )

    # Очистить Redis active_trip
    try:
        await redis_client.delete_active_trip(str(vehicle_id))
    except Exception as e:
        logger.warning(
            "Failed to delete active trip from Redis",
            vehicle_id=vehicle_id,
            error=str(e),
        )

    logger.info(
        "Trip completed",
        vehicle_id=vehicle_id,
        cycle_id=cycle_id,
        trip_type=trip.trip_type,
        original_trip_type=original_trip_type,
        task_completed=task_completed,
        task_cancelled=task_cancelled,
        next_task_id=next_task_id,
    )

    # ВАЖНО: Завершение цикла происходит в _end_cycle из state machine,
    # а не здесь, чтобы избежать двойного вызова и проблем с сессией БД

    # Публикуем событие trip_completed в MQTT
    try:
        await publish_trip_event(
            event_type="trip_completed",
            cycle_id=cycle_id,
            server_trip_id=trip.task_id,
            trip_type=trip.trip_type,
            vehicle_id=str(vehicle_id),
            place_id=place_id,
            state="unloading",
            tag=str(tag) if tag is not None else None,
            unloading_timestamp=unloading_timestamp,
        )
        logger.info(
            "Trip_completed event published successfully",
            cycle_id=cycle_id,
            vehicle_id=vehicle_id,
        )
    except Exception as e:
        logger.error(
            "Failed to publish trip_completed event",
            cycle_id=cycle_id,
            vehicle_id=vehicle_id,
            error=str(e),
            exc_info=True,
        )

    return {
        "success": True,
        "message": "Trip completed successfully",
        "trip_type": trip.trip_type,
        "task_completed": task_completed,
        "task_cancelled": task_cancelled,
        "next_task_id": None,
    }


async def _save_tag_history_from_redis(
    vehicle_id: int,
    cycle_id: str,
    db: AsyncSession,
) -> None:
    """Сохранить историю меток из Redis Stream в PostgreSQL.

    Читает все метки для цикла из Redis и сохраняет в cycle_tag_history.
    Trip ID = Cycle ID
    """
    try:
        # Получить tag_history из Redis Stream
        vehicle_id_str = str(vehicle_id)
        vehicle_id_int = int(vehicle_id_str)

        tag_history = await redis_client.get_tag_history(vehicle_id_str)

        if not tag_history:
            logger.debug(
                "No tag history to save",
                vehicle_id=vehicle_id,
                cycle_id=cycle_id,
            )
            return

        # Сохранить каждую метку в PostgreSQL
        for entry in tag_history:
            history_id = generate_uuid_vehicle_id(vehicle_id_int)
            history = CycleTagHistory(
                id=history_id,
                timestamp=datetime.fromisoformat(entry["timestamp"]),
                vehicle_id=vehicle_id_int,
                cycle_id=cycle_id,
                point_id=entry["point_id"],
                place_id=entry.get("place_id"),  # place.id из graph-service (если есть)
                extra_data=entry.get("extra_data"),
            )
            db.add(history)

        await db.commit()

        # Очистить Redis Stream после сохранения
        await redis_client.clear_tag_history(vehicle_id_str)

        logger.info(
            "Tag history saved to PostgreSQL",
            vehicle_id=vehicle_id,
            cycle_id=cycle_id,
            count=len(tag_history),
        )

    except Exception as e:
        logger.error(
            "Failed to save tag history",
            vehicle_id=vehicle_id,
            cycle_id=cycle_id,
            error=str(e),
            exc_info=True,
        )


async def get_place_remaining_history_by_trips(
    trips: list[Trip],
    db: AsyncSession,
) -> dict[str, list[PlaceRemainingHistory]]:
    """Получить историю изменений остатков мест для списка рейсов.

    Находит самый ранний start_time и самый поздний end_time среди всех рейсов,
    получает все записи PlaceRemainingHistory в этом диапазоне и группирует их по trip_id.

    Args:
        trips: Список объектов Trip
        db: Database session

    Returns:
        Словарь в формате {trip_id: [list of PlaceRemainingHistory]}
    """
    if not trips:
        logger.debug("Empty trips list provided")
        return {}

    # Найти самый ранний start_time,
    # самый поздний end_time,
    # проверить незавершенные рейсы,
    # собрать trip_cycle_ids
    start_times: list[datetime] = []
    end_times: list[datetime] = []
    trip_cycle_ids = set()

    for trip in trips:
        if trip.start_time:
            start_times.append(trip.start_time)
        if trip.end_time:
            end_times.append(trip.end_time)
        trip_cycle_ids.add(trip.cycle_id)

    if not start_times:
        logger.warning("No trips with start_time found")
        return {}

    min_start_time = min(start_times)

    if not end_times:
        logger.info(
            "No trip end_time values found; skipping place remaining history",
            trips_count=len(trips),
            start_time=min_start_time.isoformat(),
            completed_trips=0,
        )
        return {trip_id: [] for trip_id in trip_cycle_ids}

    max_end_time = max(end_times)

    logger.debug(
        "Getting place remaining history for trips",
        trips_count=len(trips),
        start_time=min_start_time.isoformat(),
        end_time=max_end_time.isoformat(),
    )

    # Получить все записи в диапазоне
    all_history = await place_remaining_service.get_by_timestamp_range(
        db=db,
        start_timestamp=min_start_time,
        end_timestamp=max_end_time,
    )

    # Сгруппировать по cycle_id (trip_id)
    result: dict[str, list[PlaceRemainingHistory]] = {trip_id: [] for trip_id in trip_cycle_ids}

    for history in all_history:
        if history.cycle_id and history.cycle_id in trip_cycle_ids:
            result[history.cycle_id].append(history)

    logger.info(
        "Place remaining history grouped by trips",
        trips_count=len(trips),
        total_history_records=len(all_history),
        grouped_records=sum(len(records) for records in result.values()),
    )

    return result


async def construct_trip_cycle_num_subquery(vehicle_id: int, timestamp: datetime) -> ScalarSelect[int] | None:
    """Сконструировать подзапрос для определения cycle_num в рамках insert() или update() запросов.

    **ВАЖНО!** ScalarSelect не пригоден для приведения к boolean (возникнет TypeError).
    Для проверки результата требуется использовать is None / is not None

    TODO: Добыть WorkRegime техники для определения корректных границ смены (сейчас между ним и Vehicle нет связи)

    Args:
        vehicle_id: ID транспорта
        timestamp: временная метка для определения границ смены

    Returns:
        ScalarSelect или None (если не удалось рассчитать границы смены)
    """
    shift_info = await enterprise_client.get_shift_info_and_time_range(timestamp)
    if not shift_info:
        logger.error(
            "Failed to get shift info, cycle_num db subquery will not be returned",
            vehicle_id=vehicle_id,
            timestamp=timestamp.isoformat(),
        )
        return None

    subquery = (
        select(func.count() + 1)
        .select_from(Trip)
        .where(
            Trip.cycle_id == Cycle.cycle_id,
            Cycle.vehicle_id == vehicle_id,
            Trip.start_time >= shift_info["start_time"],
            Trip.start_time < shift_info["end_time"],
        )
        .scalar_subquery()
    )
    return subquery


async def bulk_update_trips_cycle_num(vehicle_id: int, timestamp: datetime, db: AsyncSession) -> None:
    """Обновить счётчик cycle_num для всех рейсов смены одним запросом.

    Выполняется только db.execute(), ни db.flush(), ни db.commit() НЕ вызываются.
    Если не удастся рассчитать границы смены, то запрос не будет выполнен вообще.

    TODO: Добыть WorkRegime техники для определения корректных границ смены (сейчас между ним и Vehicle нет связи)

    Args:
        vehicle_id: ID транспорта
        timestamp: временная метка для определения границ смены
        db: Database session
    """
    shift_info = await enterprise_client.get_shift_info_and_time_range(timestamp)
    if not shift_info:
        logger.error(
            "Failed to get shift info, cycle_num db query will not be executed",
            vehicle_id=vehicle_id,
            timestamp=timestamp.isoformat(),
        )
        return

    subquery = (
        select(
            Trip.cycle_id,
            func.row_number()
            .over(
                order_by=Trip.start_time,
            )
            .label("new_number"),
        )
        .where(
            Trip.cycle_id == Cycle.cycle_id,
            Cycle.vehicle_id == vehicle_id,
            Trip.start_time >= shift_info["start_time"],
            Trip.start_time < shift_info["end_time"],
        )
        .subquery()
    )
    stmt = update(Trip).where(Trip.cycle_id == subquery.c.cycle_id).values(cycle_num=subquery.c.new_number)
    await db.execute(stmt)
