"""Event handlers для обработки событий от MQTT (Nanomq).

Связывает MQTT события с State Machine для автоматических переходов.
"""

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.mqtt_client import TripServiceMQTTClient
from app.core.redis_client import redis_client
from app.database.models import Cycle, PlaceRemainingHistory
from app.database.session import get_db_session
from app.enums import RemainingChangeTypeEnum
from app.services.place_info import recalculate_and_update_place_stock
from app.services.state_machine import State, StateMachine, TriggerType, get_state_machine

# Глобальный MQTT клиент
mqtt_client: TripServiceMQTTClient | None = None


async def _publish_tag_to_redis(topic: str, data: dict[str, Any]) -> None:
    """Публикация tag событий в Redis pub/sub для SSE.

    Это позволяет фронтенду получать обновления локации в реальном времени через SSE.
    """
    try:
        # Публикуем в Redis pub/sub канал
        channel = topic  # Используем тот же топик, что и в MQTT
        if redis_client.redis is None:
            raise RuntimeError("Redis client is not connected")
        await redis_client.redis.publish(channel, json.dumps(data))

        logger.debug(
            "Tag event published to Redis pub/sub",
            channel=channel,
            point_id=data.get("point_id"),
        )
    except Exception as e:
        logger.error(
            "Failed to publish tag event to Redis",
            error=str(e),
        )


async def _publish_weight_to_redis(topic: str, data: dict[str, Any]) -> None:
    """Публикация weight событий в Redis pub/sub и сохранение последнего значения."""
    try:
        channel = topic
        if redis_client.redis is None:
            raise RuntimeError("Redis client is not connected")
        await redis_client.redis.publish(channel, json.dumps(data))

        # Сохраняем последнее значение веса для мгновенной отдачи по SSE
        parts = topic.split("/")
        vehicle_id = parts[1] if len(parts) > 1 else None
        if vehicle_id:
            key = f"trip-service:vehicle:{vehicle_id}:current_weight"
            await redis_client.set_json(key, data)
    except Exception as e:
        logger.error(
            "Failed to publish weight event to Redis",
            error=str(e),
        )


async def handle_place_remaining_change(
    pr_data: dict[str, Any],
    context_data: dict[str, Any],
    event_timestamp: datetime,
    db: AsyncSession,
) -> None:
    """Обработка события place_remaining_change - сохранение истории и обновление graph-service.

    Args:
        pr_data: Данные place_remaining_change ({id, place_id, change_type, change_amount})
        Сохраняем в pr_data task_id и shift_id, тк они подчищаются в conext_data, при смене статусов
        context_data: Контекст события (cycle_id, task_id, vehicle_id и т.д.)
        event_timestamp: Время события
        db: Сессия БД
    """
    try:
        logger.info(
            "handle_place_remaining_change called",
            pr_data=pr_data,
            context_data=context_data,
            event_timestamp=event_timestamp.isoformat() if event_timestamp else None,
        )

        history_id = pr_data.get("id")
        place_id = pr_data.get("place_id")
        change_type = pr_data.get("change_type")
        change_amount = pr_data.get("change_amount")
        source = pr_data.get("source", "system")

        # Детальная проверка валидности данных с логированием каждого отсутствующего поля
        missing_fields = []
        if not history_id:
            missing_fields.append("id")
        if place_id is None:
            missing_fields.append("place_id")
        if not change_type:
            missing_fields.append("change_type")
        if change_amount is None:
            missing_fields.append("change_amount")

        if missing_fields:
            logger.error(
                "Invalid place_remaining_change data: missing required fields",
                missing_fields=missing_fields,
                pr_data=pr_data,
                context_data=context_data,
            )
            return

        vehicle_id = context_data.get("vehicle_id")

        if not vehicle_id:
            logger.error(
                "vehicle_id is missing in context_data",
                context_data=context_data,
                pr_data=pr_data,
            )
            return

        # Приоритетно берем task_id и shift_id из самого объекта place_remaining_change
        # (для единообразия loading и unloading), иначе из context_data (обратная совместимость)
        task_id = pr_data.get("task_id") or context_data.get("task_id")
        shift_id = pr_data.get("shift_id") or context_data.get("shift_id")
        cycle_id = pr_data.get("cycle_id") or context_data.get("cycle_id")

        # Проверка идемпотентности - если запись существует, пропускаем сохранение в БД,
        # но все равно обновляем graph-service (для случаев модификации записей)
        existing = await db.execute(
            select(PlaceRemainingHistory).where(PlaceRemainingHistory.id == history_id),
        )
        existing_record = existing.scalar_one_or_none()

        if existing_record:
            logger.warning(
                "PlaceRemainingHistory already exists, skipping DB save but updating graph-service",
                history_id=history_id,
                place_id=place_id,
            )
        else:
            # Сохранение в локальную БД
            try:
                # Проверка валидности change_type перед созданием enum
                try:
                    change_type_enum = RemainingChangeTypeEnum(str(change_type))
                except ValueError as enum_error:
                    logger.error(
                        "Invalid change_type value for PlaceRemainingHistory",
                        history_id=history_id,
                        place_id=place_id,
                        change_type=change_type,
                        valid_values=[e.value for e in RemainingChangeTypeEnum],
                        error=str(enum_error),
                        pr_data=pr_data,
                    )
                    return

                # Проверка типов данных перед созданием объекта
                if not isinstance(place_id, int):
                    logger.error(
                        "Invalid place_id type for PlaceRemainingHistory",
                        history_id=history_id,
                        place_id=place_id,
                        place_id_type=type(place_id).__name__,
                        pr_data=pr_data,
                    )
                    return

                if not isinstance(change_amount, (int, float)):
                    logger.error(
                        "Invalid change_amount type for PlaceRemainingHistory",
                        history_id=history_id,
                        place_id=place_id,
                        change_amount=change_amount,
                        change_amount_type=type(change_amount).__name__,
                        pr_data=pr_data,
                    )
                    return

                history = PlaceRemainingHistory(
                    id=history_id,
                    place_id=place_id,
                    change_type=change_type_enum,
                    change_amount=round(float(change_amount), 1),
                    timestamp=event_timestamp,
                    cycle_id=cycle_id,
                    task_id=task_id,
                    shift_id=shift_id,
                    vehicle_id=vehicle_id,
                    source=source,
                )

                db.add(history)
                await db.commit()
                logger.info(
                    "Saved PlaceRemainingHistory",
                    history_id=history_id,
                    place_id=place_id,
                    amount=change_amount,
                    source=source,
                )
            except ValueError as value_error:
                logger.error(
                    "ValueError while creating PlaceRemainingHistory record",
                    history_id=history_id,
                    place_id=place_id,
                    change_type=change_type,
                    change_amount=change_amount,
                    error=str(value_error),
                    pr_data=pr_data,
                    context_data=context_data,
                    exc_info=True,
                )
                await db.rollback()
                return
            except Exception as db_error:
                logger.error(
                    "Database error while saving PlaceRemainingHistory",
                    history_id=history_id,
                    place_id=place_id,
                    change_type=change_type,
                    change_amount=change_amount,
                    error=str(db_error),
                    error_type=type(db_error).__name__,
                    pr_data=pr_data,
                    context_data=context_data,
                    exc_info=True,
                )
                await db.rollback()
                return

        # Пересчет остатков и обновление graph-service
        try:
            if place_id is None:
                raise RuntimeError("place_id is required for stock recalculation")
            await recalculate_and_update_place_stock(place_id=int(place_id), db=db)
        except Exception as graph_error:
            logger.error(
                "Error updating graph-service place stock",
                history_id=history_id,
                place_id=place_id,
                error=str(graph_error),
                pr_data=pr_data,
                exc_info=True,
            )
            # Не прерываем выполнение, т.к. запись в БД уже сохранена

    except Exception as e:
        logger.error(
            "Unexpected error handling place_remaining_change",
            pr_data=pr_data,
            context_data=context_data,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )


async def handle_enterprise_service_event(topic: str, data: dict[str, Any], db: AsyncSession) -> None:
    """Обработчик событий enterprise-service для Bort Mode.

    Архитектура:
    1. Enterprise-service (на сервере) публикует события в серверный MQTT
    2. События синхронизируются на бортовой MQTT через MQTT bridge
    3. Бортовой trip-service получает событие через MQTT подписку
    4. Делает HTTP GET к серверному enterprise-service для получения полных данных
    5. Вызывает локальный API trip-service для создания/обновления ShiftTask

    Формат события (приходит через MQTT):
    {
      "event_type": "entity_changed",
      "entity_type": "shift_task",
      "entity_id": "056c0c5a-c8ba-456e-b573-c26e8bf60209",
      "action": "create" | "update" | "delete",
      "timestamp": "2025-11-05T06:37:31.572332",
      "data": {}
    }

    Процесс:
    1. Получить событие от enterprise-service через MQTT
    2. HTTP GET к серверному enterprise-service: /api/shift-tasks/{entity_id}
    3. В зависимости от action:
       - create: POST /api/shift-tasks (локальный API trip-service)
       - update: PUT /api/shift-tasks/{entity_id} (локальный API trip-service)
       - delete: DELETE /api/shift-tasks/{entity_id} (локальный API trip-service)

    Args:
        topic: MQTT топик (truck/{vehicle_id}/enterprise-service/events)
        data: Данные события от enterprise-service
        db: Database session
    """
    try:
        import httpx

        event_type = data.get("event_type")
        entity_type = data.get("entity_type")
        entity_id = data.get("entity_id")
        action = data.get("action")

        # Извлечь vehicle_id из топика truck/{vehicle_id}/enterprise-service/events
        parts = topic.split("/")
        vehicle_id = parts[1] if len(parts) > 1 else settings.vehicle_id

        logger.info(
            "📨 Enterprise-service event received (bort mode)",
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            vehicle_id=vehicle_id,
        )

        # Обрабатываем только shift_task события
        if event_type != "entity_changed" or entity_type != "shift_task":
            logger.debug(
                "Ignoring non-shift_task event",
                event_type=event_type,
                entity_type=entity_type,
            )
            return

        if not entity_id:
            logger.warning("Entity ID not provided in enterprise-service event", data=data)
            return

        # Делаем GET запрос к enterprise-service для получения полных данных
        enterprise_url = f"http://{settings.enterprise_service_host}:{settings.enterprise_service_port}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{enterprise_url}/api/shift-tasks/{entity_id}")

                if response.status_code != 200:
                    logger.error(
                        f"Failed to fetch shift_task from enterprise-service: "
                        f"entity_id={entity_id}, status_code={response.status_code}, "
                        f"response={response.text[:200] if response.text else 'empty'}",
                    )
                    return

                shift_task_data = response.json()
        except httpx.RequestError as e:
            logger.error(
                f"HTTP request failed to enterprise-service: "
                f"entity_id={entity_id}, url={enterprise_url}/api/shift-tasks/{entity_id}, "
                f"error={str(e)}",
            )
            return
        except Exception as e:
            logger.error(
                "Failed to parse response from enterprise-service",
                entity_id=entity_id,
                error=str(e),
            )
            return

        logger.info(
            "Fetched shift_task from enterprise-service",
            entity_id=entity_id,
            task_name=shift_task_data.get("task_name"),
            route_tasks_count=len(shift_task_data.get("route_tasks", [])),
        )

        # UNIFIED FORMAT (2025-11-10)
        # Адаптер удален! Данные от enterprise-service используются напрямую.
        # Форматы trip-service и enterprise-service теперь идентичны.

        # В зависимости от action обращаемся к API trip-service
        trip_service_url = f"http://localhost:{settings.port}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            if action == "create":
                # POST /api/shift-tasks (данные напрямую от enterprise-service)
                response = await client.post(
                    f"{trip_service_url}/api/shift-tasks",
                    json=shift_task_data,
                )
                if response.status_code in [200, 201]:
                    logger.info(
                        "ShiftTask created via API",
                        entity_id=entity_id,
                        task_name=shift_task_data.get("task_name"),
                    )
                else:
                    logger.error(
                        "Failed to create ShiftTask via API",
                        entity_id=entity_id,
                        status_code=response.status_code,
                        response=response.text,
                    )

            elif action == "update":
                # PUT /api/shift-tasks/{entity_id} (данные напрямую от enterprise-service)
                response = await client.put(
                    f"{trip_service_url}/api/shift-tasks/{entity_id}",
                    json=shift_task_data,
                )
                if response.status_code == 200:
                    logger.info(
                        "ShiftTask updated via API",
                        entity_id=entity_id,
                        task_name=shift_task_data.get("task_name"),
                    )
                else:
                    logger.error(
                        "Failed to update ShiftTask via API",
                        entity_id=entity_id,
                        status_code=response.status_code,
                        response=response.text,
                    )

            elif action == "delete":
                # DELETE /api/shift-tasks/{entity_id}
                response = await client.delete(
                    f"{trip_service_url}/api/shift-tasks/{entity_id}",
                )
                if response.status_code == 200:
                    logger.info(
                        "ShiftTask deleted via API",
                        entity_id=entity_id,
                    )
                else:
                    logger.error(
                        "Failed to delete ShiftTask via API",
                        entity_id=entity_id,
                        status_code=response.status_code,
                        response=response.text,
                    )

    except Exception as e:
        logger.error(
            "Error handling enterprise-service event",
            topic=topic,
            error=str(e),
            exc_info=True,
        )


async def _handle_cycle_started(
    vehicle_id: int,
    cycle_id: str,
    data: dict[str, Any],
    event_timestamp: datetime,
    db: AsyncSession,
) -> None:
    """Обработка события cycle_started - создание Cycle на сервере."""
    try:
        # Проверить, не существует ли уже цикл
        existing = await db.execute(
            select(Cycle).where(Cycle.cycle_id == cycle_id),
        )
        if existing.scalar_one_or_none():
            logger.debug("Cycle already exists", cycle_id=cycle_id)
            return

        # Создать Cycle
        cycle = Cycle(
            cycle_id=cycle_id,
            vehicle_id=vehicle_id,
            task_id=data.get("task_id"),
            shift_id=data.get("shift_id"),
            from_place_id=data.get("place_id"),
            cycle_started_at=event_timestamp,
            cycle_status="in_progress",
            cycle_type="normal",
            source="system",
        )

        db.add(cycle)
        await db.commit()

        logger.info(
            "Cycle created from trip-service event",
            cycle_id=cycle_id,
            vehicle_id=vehicle_id,
            from_place_id=data.get("place_id"),
        )
    except Exception as e:
        logger.error(
            "Failed to create cycle from event",
            cycle_id=cycle_id,
            vehicle_id=vehicle_id,
            error=str(e),
            exc_info=True,
        )
        await db.rollback()


async def _handle_trip_started(
    vehicle_id: int,
    cycle_id: str,
    data: dict[str, Any],
    event_timestamp: datetime,
    db: AsyncSession,
) -> None:
    """Обработка события trip_started - создание Trip на сервере через JTI."""
    try:
        from sqlalchemy import insert, select, update

        from app.database.models import Cycle, Trip
        from app.services.trip_manager import construct_trip_cycle_num_subquery

        # Проверить, существует ли Cycle
        cycle_result = await db.execute(
            select(Cycle).where(Cycle.cycle_id == cycle_id),
        )
        cycle = cycle_result.scalar_one_or_none()

        if not cycle:
            logger.warning(
                "Cycle not found for trip_started, creating cycle first",
                cycle_id=cycle_id,
            )
            # Создать Cycle если его нет
            await _handle_cycle_started(vehicle_id, cycle_id, data, event_timestamp, db)
            # Перечитать cycle
            cycle_result = await db.execute(
                select(Cycle).where(Cycle.cycle_id == cycle_id),
            )
            cycle = cycle_result.scalar_one_or_none()
            if not cycle:
                logger.error("Failed to create cycle for trip", cycle_id=cycle_id)
                return

        trip_result = await db.execute(
            select(Trip).where(Trip.cycle_id == cycle_id),
        )
        if trip_result.scalar_one_or_none():
            logger.debug("Trip already exists", cycle_id=cycle_id)
            return

        task_id_raw = data.get("task_id")
        shift_id = data.get("shift_id") or cycle.shift_id

        if task_id_raw and not cycle.task_id:
            cycle.task_id = task_id_raw if task_id_raw else None
        if shift_id and not cycle.shift_id:
            cycle.shift_id = shift_id if shift_id else None
        await db.flush()

        trip_type = "planned" if task_id_raw else "unplanned"

        # Используем loading_timestamp из данных события или event_timestamp как fallback
        loading_ts_str = data.get("loading_timestamp")
        if loading_ts_str:
            try:
                loading_timestamp = datetime.fromisoformat(loading_ts_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                loading_timestamp = event_timestamp
        else:
            loading_timestamp = event_timestamp

        # Создать Trip через JTI

        # start_time = event_timestamp (время события trip_started, переход в moving_loaded)
        # loading_timestamp = время начала погрузки (статус loading)
        cycle_num_subquery = await construct_trip_cycle_num_subquery(cycle.vehicle_id, event_timestamp)
        cycle_num = 1 if cycle_num_subquery is None else cycle_num_subquery
        await db.execute(
            insert(Trip).values(
                cycle_id=cycle_id,
                trip_type=trip_type,
                start_time=event_timestamp,
                loading_place_id=data.get("place_id"),
                loading_tag=str(data.get("tag")) if data.get("tag") is not None else None,
                loading_timestamp=loading_timestamp,
                cycle_num=cycle_num,
            ),
        )

        # Обновить entity_type для JTI
        await db.execute(
            update(Cycle).where(Cycle.cycle_id == cycle_id).values(entity_type="trip"),
        )

        await db.commit()

        logger.info(
            "Trip created from trip-service event",
            cycle_id=cycle_id,
            vehicle_id=vehicle_id,
            trip_type=trip_type,
            loading_place_id=data.get("place_id"),
            loading_tag=data.get("tag"),
        )
    except Exception as e:
        logger.error(
            "Failed to create trip from event",
            cycle_id=cycle_id,
            vehicle_id=vehicle_id,
            error=str(e),
            exc_info=True,
        )
        await db.rollback()


async def _handle_state_transition(
    vehicle_id: int,
    cycle_id: str | None,
    data: dict[str, Any],
    event_timestamp: datetime,
    db: AsyncSession,
    history_id: str,
) -> None:
    """Обработка события state_transition - сохранение в CycleStateHistory.

    Args:
        vehicle_id: ID транспортного средства
        cycle_id: ID цикла
        data: Данные события
        event_timestamp: Время события
        db: Сессия базы данных
        history_id: Обязательный UUID записи истории, сгенерированный на борту
    """
    try:
        from app.database.models import CycleStateHistory

        state_data = {
            "state": data.get("state"),
            "cycle_id": cycle_id,
            "task_id": data.get("task_id"),
            "point_id": data.get("point_id"),
            "place_id": data.get("place_id"),
        }

        place_id = data.get("place_id") or state_data.get("last_place_id")
        task_id = data.get("task_id") or state_data.get("task_id")

        history = CycleStateHistory(
            id=history_id,
            timestamp=event_timestamp,
            vehicle_id=vehicle_id,
            cycle_id=cycle_id,
            state=data.get("state", ""),
            state_data=state_data,
            place_id=place_id,
            task_id=task_id,
            trigger_type=data.get("trigger_type", "tag"),
        )

        db.add(history)
        await db.commit()

        logger.info(
            "State transition saved to CycleStateHistory",
            cycle_id=cycle_id,
            state=data.get("state"),
            history_id=history_id,
        )
    except Exception as e:
        logger.error(
            "Failed to save state transition",
            cycle_id=cycle_id,
            vehicle_id=vehicle_id,
            error=str(e),
            exc_info=True,
        )
        await db.rollback()


async def _update_trip_unloading_timestamp(
    cycle_id: str,
    unloading_timestamp: datetime,
    db: AsyncSession,
) -> None:
    """Обновить unloading_timestamp рейса при переходе в состояние unloading.

    unloading_timestamp = время начала разгрузки (статус unloading)
    """
    try:
        from sqlalchemy import select

        from app.database.models import Trip

        query = select(Trip).where(Trip.cycle_id == cycle_id)
        result = await db.execute(query)
        trip = result.scalar_one_or_none()

        if trip:
            trip.unloading_timestamp = unloading_timestamp
            await db.commit()
    except Exception as e:
        logger.error(
            "Failed to update trip unloading_timestamp",
            cycle_id=cycle_id,
            error=str(e),
            exc_info=True,
        )
        await db.rollback()


async def _handle_trip_completed(
    vehicle_id: int,
    cycle_id: str,
    data: dict[str, Any],
    event_timestamp: datetime,
    db: AsyncSession,
) -> None:
    """Обработка события trip_completed - обновление Trip на сервере."""
    try:
        from sqlalchemy import select

        from app.database.models import Trip

        trip_result = await db.execute(
            select(Trip).where(Trip.cycle_id == cycle_id),
        )
        trip = trip_result.scalar_one_or_none()

        if not trip:
            logger.warning(
                "Trip not found for trip_completed event",
                cycle_id=cycle_id,
            )
            return

        # Используем unloading_timestamp из данных события или event_timestamp как fallback
        unloading_ts_raw = data.get("unloading_timestamp")
        if isinstance(unloading_ts_raw, str):
            try:
                unloading_timestamp = datetime.fromisoformat(unloading_ts_raw.replace("Z", "+00:00"))
            except ValueError:
                unloading_timestamp = event_timestamp
        elif isinstance(unloading_ts_raw, (int, float)):
            unloading_timestamp = datetime.fromtimestamp(float(unloading_ts_raw), tz=UTC)
        else:
            unloading_timestamp = event_timestamp

        # end_time = event_timestamp (время события trip_completed, переход в moving_empty)
        trip.end_time = event_timestamp
        trip.unloading_place_id = data.get("place_id")
        tag_val = data.get("tag")
        trip.unloading_tag = str(tag_val) if tag_val is not None else None
        trip.unloading_timestamp = unloading_timestamp

        await db.commit()

        logger.info(
            "Trip updated from trip_completed event",
            cycle_id=cycle_id,
            vehicle_id=vehicle_id,
            unloading_place_id=data.get("place_id"),
            unloading_tag=data.get("tag"),
            unloading_timestamp=unloading_timestamp.isoformat(),
        )
    except Exception as e:
        logger.error(
            "Failed to update trip from event",
            cycle_id=cycle_id,
            vehicle_id=vehicle_id,
            error=str(e),
            exc_info=True,
        )
        await db.rollback()


async def _handle_cycle_completed(
    vehicle_id: int,
    cycle_id: str,
    data: dict[str, Any],
    event_timestamp: datetime,
    db: AsyncSession,
) -> None:
    """Обработка события cycle_completed - обновление Cycle на сервере."""
    try:
        from sqlalchemy import select

        from app.database.models import Cycle, Trip

        cycle_result = await db.execute(
            select(Cycle).where(Cycle.cycle_id == cycle_id),
        )
        cycle = cycle_result.scalar_one_or_none()

        if not cycle:
            logger.warning(
                "Cycle not found for cycle_completed event",
                cycle_id=cycle_id,
            )
            return

        cycle.cycle_completed_at = event_timestamp
        cycle.to_place_id = data.get("place_id")
        cycle.cycle_status = "completed"

        unloading_ts_raw = data.get("unloading_timestamp")
        unloading_timestamp: datetime | None = None
        if isinstance(unloading_ts_raw, str):
            try:
                unloading_timestamp = datetime.fromisoformat(unloading_ts_raw.replace("Z", "+00:00"))
            except ValueError:
                unloading_timestamp = None
        elif isinstance(unloading_ts_raw, (int, float)):
            unloading_timestamp = datetime.fromtimestamp(float(unloading_ts_raw), tz=UTC)

        if unloading_timestamp:
            trip_result = await db.execute(
                select(Trip).where(Trip.cycle_id == cycle_id),
            )
            trip = trip_result.scalar_one_or_none()
            if trip:
                trip.unloading_timestamp = unloading_timestamp

        await db.commit()

        logger.info(
            "Cycle updated from cycle_completed event",
            cycle_id=cycle_id,
            vehicle_id=vehicle_id,
            to_place_id=data.get("place_id"),
            unloading_timestamp=unloading_timestamp.isoformat() if unloading_timestamp else None,
        )
    except Exception as e:
        logger.error(
            "Failed to update cycle from event",
            cycle_id=cycle_id,
            vehicle_id=vehicle_id,
            error=str(e),
            exc_info=True,
        )
        await db.rollback()


async def handle_trip_service_event(topic: str, data: dict[str, Any], db: AsyncSession) -> None:
    """Обработчик событий trip-service от бортов (только Server Mode).

    Обрабатывает события от бортов для воссоздания циклов, рейсов и их статистики на сервере.

    Формат события:
    {
      "event_type": "state_transition" | "trip_started" | "trip_completed" | "cycle_started" | "cycle_completed",
      "state": "moving_loaded",
      "cycle_id": "cy_abc123",
      "task_id": "task_001",
      "trip_type": "planned" | "unplanned" (опционально, только для рейсов),
      "timestamp": 1699356000.123,
      "point_id": "point_42"
    }

    Типы событий:
    - cycle_started: начало цикла (при создании цикла)
    - cycle_completed: завершение цикла (при завершении цикла)
    - trip_started: начало рейса (при создании рейса внутри цикла)
    - trip_completed: завершение рейса (при завершении рейса)
    - state_transition: переход состояния (при каждом изменении состояния)

    Args:
        topic: MQTT топик (truck/{vehicle_id}/trip-service/events)
        data: Данные события от бортового trip-service
        db: Database session
    """
    try:
        from datetime import datetime

        from app.database.models import CycleStateHistory

        event_type = data.get("event_type")
        cycle_id: str | None = str(data["cycle_id"]) if data.get("cycle_id") is not None else None

        # Извлечь vehicle_id из топика truck/{vehicle_id}/trip-service/events
        parts = topic.split("/")
        vehicle_id = int(parts[1] if len(parts) > 1 else "unknown")

        # Конвертировать timestamp в datetime
        timestamp_float = data.get("timestamp")
        if timestamp_float:
            event_timestamp = datetime.fromtimestamp(timestamp_float, tz=UTC)
        else:
            event_timestamp = datetime.now(UTC)

        logger.info(
            "📨 [SERVER] Trip-service event received (server mode)",
            event_type=event_type,
            cycle_id=cycle_id,
            vehicle_id=vehicle_id,
            state=data.get("state"),
            task_id=data.get("task_id"),
            has_place_remaining_change="place_remaining_change" in data,
            data_keys=list(data.keys()) if isinstance(data, dict) else None,
            data_full=data,
        )

        # Обработка изменения остатков (place_remaining_change)
        place_remaining_change = data.get("place_remaining_change")
        logger.info(
            "🔍 [SERVER] Checking place_remaining_change in event",
            vehicle_id=vehicle_id,
            cycle_id=cycle_id,
            event_type=event_type,
            has_place_remaining_change=place_remaining_change is not None,
            place_remaining_change_data=place_remaining_change,
            place_remaining_change_type=type(place_remaining_change).__name__
            if place_remaining_change is not None
            else None,
            data_has_key="place_remaining_change" in data if isinstance(data, dict) else False,
        )
        if place_remaining_change:
            # Подготавливаем контекст
            context_data = {
                "vehicle_id": vehicle_id,
                "cycle_id": cycle_id,
                "task_id": data.get("task_id"),
                "shift_id": data.get("shift_id"),
            }
            await handle_place_remaining_change(
                place_remaining_change,
                context_data,
                event_timestamp,
                db,
            )

        # Обработка событий по типам
        logger.debug(
            "Processing event",
            event_type=event_type,
            cycle_id=cycle_id,
            vehicle_id=vehicle_id,
        )

        if event_type == "cycle_started":
            if cycle_id:
                await _handle_cycle_started(vehicle_id, cycle_id, data, event_timestamp, db)

        elif event_type == "trip_started":
            if cycle_id:
                await _handle_trip_started(vehicle_id, cycle_id, data, event_timestamp, db)

        elif event_type == "state_transition":
            history_id = data.get("history_id")
            if not history_id:
                logger.error(
                    "Missing required history_id in state_transition event",
                    vehicle_id=vehicle_id,
                    cycle_id=cycle_id,
                    event_type=event_type,
                )
                raise ValueError(
                    f"history_id is required for state_transition events, vehicle_id={vehicle_id}, cycle_id={cycle_id}",
                )
            await _handle_state_transition(vehicle_id, cycle_id, data, event_timestamp, db, history_id)

            # При переходе в unloading - записываем unloading_timestamp в рейс
            state = data.get("state")
            if state == "unloading" and cycle_id:
                await _update_trip_unloading_timestamp(cycle_id, event_timestamp, db)
                logger.warning("Update unload timestamp")

            try:
                state_machine = StateMachine(vehicle_id=vehicle_id)
                await state_machine._publish_sse_event(
                    state=State(data.get("state", "idle")),
                    state_data={
                        "cycle_id": cycle_id,
                        "task_id": data.get("task_id"),
                        "trip_type": data.get("trip_type"),
                        "last_tag_id": data.get("tag_id"),
                        "last_place_id": data.get("place_id"),
                    },
                    trigger_type=TriggerType(data.get("trigger_type", "tag")),
                    trigger_data={
                        "tag_id": data.get("tag_id"),
                        "place_id": data.get("place_id"),
                        "tag": data.get("tag"),
                    },
                    history_id=history_id,
                )
            except Exception as publish_error:
                logger.warning(
                    "Failed to publish server-side state transition",
                    vehicle_id=vehicle_id,
                    cycle_id=cycle_id,
                    error=str(publish_error),
                )

        elif event_type == "trip_completed":
            if cycle_id:
                await _handle_trip_completed(vehicle_id, cycle_id, data, event_timestamp, db)

        elif event_type == "cycle_completed":
            if cycle_id:
                await _handle_cycle_completed(vehicle_id, cycle_id, data, event_timestamp, db)

        if event_type == "trip_completed":  # TODO проверить, всё ли атрибуты рейса пишутся
            from sqlalchemy import select

            from app.database.models import CycleAnalytics, CycleStateHistory

            # Проверить, не создана ли уже аналитика для этого цикла
            existing = await db.execute(
                select(CycleAnalytics).where(CycleAnalytics.cycle_id == cycle_id),
            )
            if existing.scalar_one_or_none():
                logger.debug("Analytics already exists for cycle", cycle_id=cycle_id)
                return

            # Получить историю состояний для цикла
            state_history_result = await db.execute(
                select(CycleStateHistory)
                .where(CycleStateHistory.cycle_id == cycle_id)
                .order_by(CycleStateHistory.timestamp),
            )
            state_history = state_history_result.scalars().all()

            if not state_history:
                logger.warning("No state history found for cycle", cycle_id=cycle_id)
                return

            # Вычислить длительности состояний
            durations = calculate_state_durations(state_history)

            # Создать запись аналитики
            analytics = CycleAnalytics(
                cycle_id=cycle_id,
                vehicle_id=vehicle_id,
                trip_type=data.get("trip_type"),
                **durations,
            )

            db.add(analytics)
            await db.commit()

            logger.info(
                "CycleAnalytics created from trip-service event",
                cycle_id=cycle_id,
                vehicle_id=vehicle_id,
            )

    except Exception as e:
        logger.error(
            "Error handling trip-service event",
            topic=topic,
            error=str(e),
            exc_info=True,
        )


async def handle_mqtt_event(topic: str, data: dict[str, Any]) -> None:
    """Обработчик событий от MQTT.

    Определяет тип события по топику и вызывает соответствующий обработчик State Machine.

    Формат сообщений от eKuiper:
    {
      "metadata": {"vehicle_id": "АС26", "sensor_type": "weight", "timestamp": 1756438176},
      "data": {"status": "loaded", "avg_weight": 207.9}
    }

    Args:
        topic: MQTT топик
        data: Данные события от eKuiper
    """
    try:
        has_enterprise = "enterprise-service/events" in topic
        has_trip_service = "trip-service/events" in topic

        # Детальное логирование для trip-service событий (серверный режим)
        if has_trip_service:
            logger.info(
                "🔍 [SERVER] handle_mqtt_event: trip-service event",
                topic=topic,
                mode=settings.service_mode,
                event_type=data.get("event_type"),
                has_place_remaining_change="place_remaining_change" in data,
                place_remaining_change=data.get("place_remaining_change"),
                data_keys=list(data.keys()) if isinstance(data, dict) else None,
                data_full=data,
            )
        else:
            logger.debug(
                f"MQTT event received: topic={topic}, mode={settings.service_mode}, "
                f"has_enterprise={has_enterprise}, has_trip_service={has_trip_service}",
            )

        # Получаем database session
        db_gen = get_db_session()
        db = await anext(db_gen)

        try:
            # Server Mode: обработка событий от бортов
            if settings.service_mode == "server" and has_trip_service:
                await handle_trip_service_event(topic, data, db)
                return

            # Bort Mode: обработка событий от enterprise-service
            # Enterprise-service публикует события в серверный MQTT,
            # они приходят на борт через MQTT bridge
            if settings.service_mode == "bort" and has_enterprise:
                logger.info("📨 Dispatching to enterprise-service handler", topic=topic)
                await handle_enterprise_service_event(topic, data, db)
                return

            # State Machine только в bort режиме
            if settings.service_mode == "bort":
                state_machine = get_state_machine(int(settings.vehicle_id))

            # Извлекаем данные из структуры eKuiper
            # Если данные уже плоские (для совместимости с тестами), используем их как есть
            if "data" in data and "metadata" in data:
                # Формат от eKuiper: {"metadata": {...}, "data": {...}}
                sensor_data = data["data"].copy()
                metadata = data["metadata"]

                # Нормализуем данные: avg_weight → value, avg_speed → value
                if "avg_weight" in sensor_data:
                    sensor_data["value"] = sensor_data["avg_weight"]
                if "avg_speed" in sensor_data:
                    sensor_data["value"] = sensor_data["avg_speed"]

                logger.debug(
                    "📨 eKuiper message received",
                    topic=topic,
                    sensor_type=metadata.get("sensor_type"),
                    vehicle_id=metadata.get("vehicle_id"),
                    status=sensor_data.get("status"),
                )
            else:
                # Формат от тестов: плоская структура
                sensor_data = data
                logger.debug("📨 Test message received", topic=topic)

            # Определяем тип события по топику (только для Bort Mode)
            if settings.service_mode == "bort":
                if "tag/raw" in topic or "tag/events" in topic:
                    await state_machine.handle_tag_event(sensor_data, db=db)
                    # Публикуем tag события в Redis pub/sub для SSE (только Bort)
                    await _publish_tag_to_redis(topic, sensor_data)

                # State Machine обработка только в bort режиме
                elif "speed/events" in topic:
                    await state_machine.handle_speed_event(sensor_data, db=db)

                elif "weight/events" in topic:
                    await state_machine.handle_weight_event(sensor_data, db=db)
                    await _publish_weight_to_redis(topic, sensor_data)

                elif "vibro/events" in topic:
                    await state_machine.handle_vibro_event(sensor_data, db=db)

                elif "fuel/events" in topic:
                    await state_machine.handle_fuel_event(sensor_data, db=db)

                else:
                    logger.warning(
                        "Unknown MQTT topic",
                        topic=topic,
                    )

            else:
                logger.warning(
                    "Unknown MQTT topic (server mode)",
                    topic=topic,
                )

        finally:
            # Закрываем database session
            await db.close()

    except Exception as e:
        logger.error(
            "Error handling MQTT event",
            topic=topic,
            error=str(e),
            exc_info=True,
        )


def calculate_state_durations(state_history: Sequence[Any]) -> dict[str, Any]:
    """Вычислить длительности состояний из истории переходов.

    Args:
        state_history: Список записей CycleStateHistory, отсортированных по timestamp

    Returns:
        dict: Словарь с длительностями каждого состояния в секундах
    """
    durations = {
        "moving_empty_duration_seconds": 0.0,
        "stopped_empty_duration_seconds": 0.0,
        "loading_duration_seconds": 0.0,
        "moving_loaded_duration_seconds": 0.0,
        "stopped_loaded_duration_seconds": 0.0,
        "unloading_duration_seconds": 0.0,
        "total_duration_seconds": 0.0,
        "state_transitions_count": len(state_history),
    }

    if not state_history:
        return durations

    # Начало и конец цикла
    cycle_started_at = state_history[0].timestamp
    cycle_completed_at = state_history[-1].timestamp
    durations["cycle_started_at"] = cycle_started_at
    durations["cycle_completed_at"] = cycle_completed_at
    durations["total_duration_seconds"] = (cycle_completed_at - cycle_started_at).total_seconds()

    # Вычислить длительность каждого состояния
    for i in range(len(state_history) - 1):
        current = state_history[i]
        next_record = state_history[i + 1]

        duration = (next_record.timestamp - current.timestamp).total_seconds()
        state = current.state

        if state == "moving_empty":
            durations["moving_empty_duration_seconds"] += duration
        elif state == "stopped_empty":
            durations["stopped_empty_duration_seconds"] += duration
        elif state == "loading":
            durations["loading_duration_seconds"] += duration
        elif state == "moving_loaded":
            durations["moving_loaded_duration_seconds"] += duration
        elif state == "stopped_loaded":
            durations["stopped_loaded_duration_seconds"] += duration
        elif state == "unloading":
            durations["unloading_duration_seconds"] += duration

    return durations


async def initialize_mqtt_client() -> TripServiceMQTTClient:
    """Инициализация и подключение MQTT клиента.

    Returns:
        Экземпляр TripServiceMQTTClient
    """
    global mqtt_client

    try:
        # Создаем MQTT клиент с event handler
        mqtt_client = TripServiceMQTTClient(
            vehicle_id=settings.vehicle_id,
            host=settings.nanomq_host,
            port=settings.nanomq_port,
            event_handler=handle_mqtt_event,
        )

        # Подключаемся к Nanomq
        await mqtt_client.connect()

        logger.info("MQTT client initialized and connected")

        return mqtt_client

    except Exception as e:
        logger.error(
            "Failed to initialize MQTT client",
            error=str(e),
            exc_info=True,
        )
        raise


async def subscribe_to_nanomq_topics() -> None:
    """Подписка на топики Nanomq.

    MQTT клиент автоматически подписывается при подключении в on_connect callback.
    Эта функция является placeholder для будущих дополнительных подписок.
    """
    logger.info("Subscribed to Nanomq topics (handled by MQTT client)")


async def disconnect_mqtt_client() -> None:
    """Отключение от MQTT брокера."""
    global mqtt_client

    if mqtt_client:
        await mqtt_client.disconnect()
        logger.info("MQTT client disconnected")
