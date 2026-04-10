"""Сервис для публикации MQTT событий при изменении shift_tasks и route_tasks.

Публикует события в MQTT топик для отправки на борт через существующий механизм trip-service.
В server режиме также публикует события в Redis для SSE.
"""

import json
from datetime import datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas.tasks.shift_tasks import ShiftTaskResponse
from app.core.config import settings
from app.core.mqtt_client import TripServiceMQTTClient
from app.core.redis_client import redis_client
from app.database.models import RouteTask, ShiftTask


# TODO Нигде не используется, отовсюду вырезан
class TaskEventPublisher:
    """Публикатор событий для shift_tasks и route_tasks.

    Публикует события в MQTT топик для отправки на борт.
    """

    @staticmethod
    async def publish_shift_task_changed(
        shift_task: ShiftTask,
        action: str,
        db: AsyncSession,
    ) -> None:
        """Публиковать событие изменения shift_task в MQTT.

        Args:
            shift_task: Объект ShiftTask
            action: Действие ("create", "update", "delete")
            db: Сессия БД
        """
        try:
            # Получаем vehicle_id из shift_task
            vehicle_id = shift_task.vehicle_id

            # Создаем payload события
            payload = {
                "event_type": "entity_changed",
                "entity_type": "shift_task",
                "entity_id": shift_task.id,
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    # Дополнительные данные если нужны
                },
            }

            # Определяем MQTT топик
            topic = f"truck/{vehicle_id}/trip-service/events"

            # Публикуем через MQTT клиент
            mqtt_client = TripServiceMQTTClient(
                vehicle_id=str(vehicle_id),
                host=settings.nanomq_host,
                port=settings.nanomq_port,
            )

            await mqtt_client.connect()
            try:
                await mqtt_client.publish(topic, payload)
                logger.info(
                    "Shift task event published to MQTT",
                    shift_task_id=shift_task.id,
                    vehicle_id=vehicle_id,
                    action=action,
                    topic=topic,
                )
            finally:
                await mqtt_client.disconnect()

            # Публикуем в Redis для SSE (только в server режиме)
            if settings.service_mode == "server":
                try:
                    logger.debug(f"Preparing Redis event for shift_task {shift_task.id}, action={action}")
                    # Сериализуем shift_task через ShiftTaskResponse (загрузит route_tasks через relationship)
                    shift_task_data = ShiftTaskResponse.model_validate(shift_task).model_dump(mode="json")
                    logger.debug(
                        f"ShiftTaskResponse serialized, route_tasks count: "
                        f"{len(shift_task_data.get('route_tasks', []))}",
                    )

                    # Формируем событие для Redis
                    redis_event = {
                        "event_type": "shift_task_changed",
                        "action": action,
                        "shift_task_id": shift_task.id,
                        "vehicle_id": vehicle_id,
                        "shift_task": shift_task_data,
                        "timestamp": datetime.utcnow().isoformat(),
                    }

                    # Публикуем в Redis канал
                    channel = "trip-service:shift_tasks:changes"
                    # Проверяем, что Redis подключен
                    if redis_client.redis is None:
                        logger.warning(
                            "Redis client not connected, skipping Redis publish",
                            shift_task_id=shift_task.id,
                        )
                    else:
                        subscribers = await redis_client.redis.publish(
                            channel,
                            json.dumps(redis_event),
                        )
                        logger.info(
                            "Shift task event published to Redis",
                            shift_task_id=shift_task.id,
                            channel=channel,
                            action=action,
                            subscribers=subscribers,
                            route_tasks_count=len(shift_task_data.get("route_tasks", [])),
                        )
                except Exception as redis_error:
                    # Логируем ошибку, но не прерываем выполнение запроса
                    logger.error(
                        "Failed to publish shift task event to Redis",
                        shift_task_id=shift_task.id,
                        error=str(redis_error),
                        exc_info=True,
                    )

        except Exception as e:
            # Логируем ошибку, но не прерываем выполнение запроса
            logger.error(
                "Failed to publish shift task event to MQTT",
                shift_task_id=shift_task.id if shift_task else None,
                action=action,
                error=str(e),
                exc_info=True,
            )

    @staticmethod
    async def publish_route_task_changed(
        route_task: RouteTask,
        action: str,
        db: AsyncSession,
    ) -> None:
        """Публиковать событие изменения route_task в MQTT.

        Args:
            route_task: Объект RouteTask
            action: Действие ("create", "update", "delete")
            db: Сессия БД
        """
        try:
            # Получаем vehicle_id через shift_task
            if not route_task.shift_task_id:
                logger.warning(
                    "Route task has no shift_task_id, skipping MQTT publish",
                    route_task_id=route_task.id,
                )
                return

            # Загружаем shift_task из БД для получения vehicle_id
            query = select(ShiftTask).where(ShiftTask.id == route_task.shift_task_id)
            result = await db.execute(query)
            shift_task = result.scalar_one_or_none()

            if not shift_task:
                logger.warning(
                    "Shift task not found for route task, skipping MQTT publish",
                    route_task_id=route_task.id,
                    shift_task_id=route_task.shift_task_id,
                )
                return

            vehicle_id = shift_task.vehicle_id

            # Создаем payload события
            payload = {
                "event_type": "entity_changed",
                "entity_type": "route_task",
                "entity_id": route_task.id,
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "shift_task_id": route_task.shift_task_id,
                    # Дополнительные данные если нужны
                },
            }

            # Определяем MQTT топик
            topic = f"truck/{vehicle_id}/trip-service/events"

            # Публикуем через MQTT клиент
            mqtt_client = TripServiceMQTTClient(
                vehicle_id=str(vehicle_id),
                host=settings.nanomq_host,
                port=settings.nanomq_port,
            )

            await mqtt_client.connect()
            try:
                await mqtt_client.publish(topic, payload)
                logger.info(
                    "Route task event published to MQTT",
                    route_task_id=route_task.id,
                    vehicle_id=vehicle_id,
                    action=action,
                    topic=topic,
                )
            finally:
                await mqtt_client.disconnect()

            # Публикуем в Redis для SSE (только в server режиме, публикуем весь shift_task)
            if settings.service_mode == "server":
                try:
                    # Загружаем shift_task с route_tasks через selectinload
                    query = (
                        select(ShiftTask)
                        .options(selectinload(ShiftTask.route_tasks))
                        .where(
                            ShiftTask.id == route_task.shift_task_id,
                        )
                    )
                    result = await db.execute(query)
                    shift_task = result.scalar_one_or_none()

                    if shift_task:
                        # Сериализуем shift_task через ShiftTaskResponse
                        shift_task_data = ShiftTaskResponse.model_validate(shift_task).model_dump(mode="json")

                        # Формируем событие для Redis (публикуем весь shift_task)
                        redis_event = {
                            "event_type": "shift_task_changed",
                            "action": "update",  # route_task изменился, значит shift_task обновился
                            "shift_task_id": shift_task.id,
                            "vehicle_id": vehicle_id,
                            "shift_task": shift_task_data,
                            "timestamp": datetime.utcnow().isoformat(),
                        }

                        # Публикуем в Redis канал
                        channel = "trip-service:shift_tasks:changes"
                        if redis_client.redis is None:
                            raise RuntimeError("redis_client.redis is not initialized")
                        await redis_client.redis.publish(
                            channel,
                            json.dumps(redis_event),
                        )

                        logger.debug(
                            "Route task change published to Redis as shift_task update",
                            route_task_id=route_task.id,
                            shift_task_id=shift_task.id,
                            channel=channel,
                        )
                except Exception as redis_error:
                    logger.error(
                        "Failed to publish route task event to Redis",
                        route_task_id=route_task.id,
                        error=str(redis_error),
                        exc_info=True,
                    )

        except Exception as e:
            # Логируем ошибку, но не прерываем выполнение запроса
            logger.error(
                "Failed to publish route task event to MQTT",
                route_task_id=route_task.id if route_task else None,
                action=action,
                error=str(e),
                exc_info=True,
            )

    @staticmethod
    async def publish_route_tasks_batch(
        route_tasks: list[RouteTask],
        action: str,
        db: AsyncSession,
    ) -> None:
        """Публиковать события для нескольких route_tasks (batch).

        Оптимизация: группирует по vehicle_id и публикует за один раз.

        Args:
            route_tasks: Список объектов RouteTask
            action: Действие ("create", "update", "delete", "upsert")
            db: Сессия БД
        """
        if not route_tasks:
            return

        try:
            # Группировка по shift_task_id для получения vehicle_id
            shift_task_ids = {rt.shift_task_id for rt in route_tasks if rt.shift_task_id}

            if not shift_task_ids:
                logger.warning("No valid shift_task_ids in route_tasks batch")
                return

            # Загружаем shift_tasks для получения vehicle_id
            query = select(ShiftTask).where(ShiftTask.id.in_(shift_task_ids))
            result = await db.execute(query)
            shift_tasks = {st.id: st for st in result.scalars().all()}

            # Группируем route_tasks по vehicle_id
            tasks_by_vehicle: dict[int, list[RouteTask]] = {}
            for rt in route_tasks:
                shift_task = shift_tasks.get(rt.shift_task_id)
                if not shift_task:
                    logger.warning(
                        "Shift task not found for route task in batch",
                        route_task_id=str(rt.id),
                        shift_task_id=rt.shift_task_id,
                    )
                    continue

                vehicle_id = shift_task.vehicle_id
                if vehicle_id not in tasks_by_vehicle:
                    tasks_by_vehicle[vehicle_id] = []
                tasks_by_vehicle[vehicle_id].append(rt)

            # Публикуем для каждого vehicle_id
            for vehicle_id, vehicle_tasks in tasks_by_vehicle.items():
                try:
                    # Создаем payload для batch
                    payload = {
                        "event_type": "entities_changed",
                        "entity_type": "route_task",
                        "action": action,
                        "timestamp": datetime.utcnow().isoformat(),
                        "count": len(vehicle_tasks),
                        "entity_ids": [str(rt.id) for rt in vehicle_tasks],
                        "data": {
                            # Дополнительные данные если нужны
                        },
                    }

                    # Определяем MQTT топик
                    topic = f"truck/{vehicle_id}/trip-service/events"

                    # Публикуем через MQTT клиент
                    mqtt_client = TripServiceMQTTClient(
                        vehicle_id=str(vehicle_id),
                        host=settings.nanomq_host,
                        port=settings.nanomq_port,
                    )

                    await mqtt_client.connect()
                    try:
                        await mqtt_client.publish(topic, payload)
                        logger.info(
                            "Route tasks batch event published to MQTT",
                            vehicle_id=vehicle_id,
                            action=action,
                            count=len(vehicle_tasks),
                            topic=topic,
                        )
                    finally:
                        await mqtt_client.disconnect()

                    # Публикуем в Redis для SSE (только в server режиме)
                    if settings.service_mode == "server":
                        try:
                            # Получаем уникальные shift_task_id из vehicle_tasks
                            vehicle_shift_task_ids = {rt.shift_task_id for rt in vehicle_tasks if rt.shift_task_id}

                            # Загружаем shift_tasks с route_tasks через selectinload
                            query = (
                                select(ShiftTask)
                                .options(selectinload(ShiftTask.route_tasks))
                                .where(
                                    ShiftTask.id.in_(vehicle_shift_task_ids),
                                )
                            )
                            result = await db.execute(query)
                            vehicle_shift_tasks = result.scalars().all()

                            # Публикуем каждый shift_task отдельно
                            for shift_task in vehicle_shift_tasks:
                                shift_task_data = ShiftTaskResponse.model_validate(shift_task).model_dump(mode="json")

                                redis_event = {
                                    "event_type": "shift_task_changed",
                                    "action": action,
                                    "shift_task_id": shift_task.id,
                                    "vehicle_id": vehicle_id,
                                    "shift_task": shift_task_data,
                                    "timestamp": datetime.utcnow().isoformat(),
                                }

                                channel = "trip-service:shift_tasks:changes"
                                if redis_client.redis is None:
                                    raise RuntimeError("redis_client.redis is not initialized")
                                await redis_client.redis.publish(
                                    channel,
                                    json.dumps(redis_event),
                                )

                            logger.debug(
                                "Route tasks batch change published to Redis",
                                vehicle_id=vehicle_id,
                                count=len(vehicle_shift_tasks),
                                channel=channel,
                            )
                        except Exception as redis_error:
                            logger.error(
                                "Failed to publish route tasks batch to Redis",
                                vehicle_id=vehicle_id,
                                error=str(redis_error),
                                exc_info=True,
                            )

                except Exception as vehicle_error:
                    logger.error(
                        "Failed to publish route tasks batch for vehicle",
                        vehicle_id=vehicle_id,
                        count=len(vehicle_tasks),
                        error=str(vehicle_error),
                        exc_info=True,
                    )

        except Exception as e:
            logger.error(
                "Failed to publish route tasks batch to MQTT",
                count=len(route_tasks),
                action=action,
                error=str(e),
                exc_info=True,
            )
