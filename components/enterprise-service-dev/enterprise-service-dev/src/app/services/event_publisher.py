"""EventPublisher - публикация событий изменений в Redis и MQTT."""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.mqtt_client import EnterpriseServiceMQTTClient


@dataclass
class EventConfig:
    """Конфигурация каналов публикации."""

    redis_channel: str = "entity_changed"
    mqtt_channel: str = "entity_changed"
    static_data_channel: str = "static_data_update"


@dataclass
class PublicationFlags:
    """Флаги управления отправкой сообщений."""

    send_to_redis: bool = True
    send_to_mqtt: bool = False


class EventPublisher:
    """Публикатор событий для уведомления других сервисов об изменениях."""

    def __init__(
        self,
        redis_client: Any = None,
    ) -> None:
        """Инициализация издателя.

        Args:
            redis_client: Redis client для pub/sub
        """
        self.redis = redis_client
        self.config = EventConfig()

    def _create_event_payload(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        action: str,
        data: dict[str, Any] | None = None,
        enterprise_id: int | None = None,
        update_type: str | None = None,
    ) -> dict[str, Any]:
        """Создание payload события."""
        payload = {
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data or {},
        }

        if enterprise_id is not None:
            payload["enterprise_id"] = enterprise_id  # type: ignore[assignment]
        if update_type is not None:
            payload["update_type"] = update_type

        return payload

    async def _publish_to_redis(
        self,
        channel: str,
        payload: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        """Публикация события в Redis."""
        if not self.redis:
            logger.warning("Redis client not available, skipping Redis publication")
            return False

        try:
            await self.redis.publish(channel, json.dumps(payload))
            logger.info(
                "Event published to Redis",
                channel=channel,
                **context,
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to publish event to Redis",
                channel=channel,
                error=str(e),
                **context,
                exc_info=True,
            )
            return False

    async def _get_vehicle_id_for_entity(
        self,
        entity_type: str,
        entity_id: str,
        db: AsyncSession,
    ) -> int | None:
        """Получить id техники для сущности в зависимости от её типа.

        Args:
            entity_type: тип сущности (vehicle и т.д.)
            entity_id: ID сущности
            db: сессия базы данных

        Returns:
            vehicle_id или None если связи с транспортом нет
        """
        try:
            # Импортируем модели локально, чтобы избежать циклических импортов
            from app.database.models import Vehicle

            if entity_type == "vehicle":
                result = await db.execute(
                    select(Vehicle.id).where(Vehicle.id == int(entity_id)),
                )
                vehicle_id = result.scalar_one_or_none()
                return vehicle_id

            else:
                # Для других типов (work_regime, status) нет связи с техникой
                logger.debug(
                    "Entity type has no vehicle relation, skipping MQTT",
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
                return None

        except Exception as e:
            logger.error(
                "Failed to get vehicle id for entity",
                entity_type=entity_type,
                entity_id=entity_id,
                error=str(e),
                exc_info=True,
            )
            return None

    async def _get_all_vehicle_ids(
        self,
        db: AsyncSession,
    ) -> list[int]:
        """Получить id всей доступной техники.

        Используется для сущностей без прямой связи с транспортом.
        """
        try:
            from app.database.models import Vehicle

            result = await db.execute(
                select(Vehicle.id),
            )
            vehicle_ids = [row[0] for row in result.all() if row[0] is not None]

            if not vehicle_ids:
                logger.warning("No vehicles found for MQTT broadcast")

            return vehicle_ids
        except Exception as e:
            logger.error(
                "Failed to fetch vehicle id list for MQTT broadcast",
                error=str(e),
                exc_info=True,
            )
            return []

    async def _publish_single_vehicle_id(
        self,
        vehicle_id: int,
        payload: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        """Публикует событие в MQTT для конкретного vehicle_id."""
        mqtt_topic = f"truck/{vehicle_id}/enterprise-service/events"
        mqtt = None
        try:
            mqtt = EnterpriseServiceMQTTClient(vehicle_id=str(vehicle_id))
            await mqtt.connect()
            await mqtt.publish(mqtt_topic, payload)
            logger.info(
                "Event published to MQTT",
                topic=mqtt_topic,
                vehicle_id=vehicle_id,
                **context,
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to publish event to MQTT",
                topic=mqtt_topic,
                vehicle_id=vehicle_id,
                error=str(e),
                **context,
                exc_info=True,
            )
            return False
        finally:
            if mqtt:
                try:
                    await mqtt.disconnect()
                except Exception as e:
                    logger.warning(
                        "Error disconnecting MQTT client",
                        vehicle_id=vehicle_id,
                        error=str(e),
                    )

    async def _publish_to_mqtt(
        self,
        channel: str,
        payload: dict[str, Any],
        context: dict[str, Any],
        db: AsyncSession,
    ) -> bool:
        """Публикация события в MQTT."""
        entity_id = str(payload.get("entity_id", ""))
        entity_type = str(payload.get("entity_type", ""))

        if not entity_id or entity_id == "unknown":
            logger.warning(
                "MQTT client not created: invalid entity_id",
                entity_id=entity_id,
                entity_type=entity_type,
            )
            return False

        # Получаем id техники для сущности
        vehicle_id = await self._get_vehicle_id_for_entity(entity_type, entity_id, db)
        vehicle_ids: list[int] = []

        if vehicle_id is not None:
            vehicle_ids = [vehicle_id]
        else:
            vehicle_ids = await self._get_all_vehicle_ids(db)
            if vehicle_ids:
                logger.info(
                    "MQTT broadcast: entity has no vehicle id, sending to all vehicles",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    total=len(vehicle_ids),
                )
            else:
                logger.warning(
                    "Skipping MQTT publish: no vehicle id data available",
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
                return False

        publish_results = []
        for current_vehicle_id in vehicle_ids:
            result = await self._publish_single_vehicle_id(
                vehicle_id=current_vehicle_id,
                payload=payload,
                context=context,
            )
            publish_results.append(result)

        return any(publish_results)

    async def _publish_parallel(
        self,
        tasks: list[asyncio.Task[Any]],
        context: dict[str, Any],
        timeout: float = 10.0,
    ) -> None:
        """Параллельное выполнение задач публикации с обработкой ошибок."""
        if not tasks:
            return

        try:
            # Запускаем все задачи параллельно
            done, pending = await asyncio.wait(
                tasks,
                timeout=timeout,
                return_when=asyncio.ALL_COMPLETED,
            )

            # Отменяем незавершенные задачи
            for task in pending:
                task.cancel()

            # Обрабатываем результаты
            for task in done:
                try:
                    await task
                except Exception as e:
                    logger.error(
                        "Publication task failed",
                        error=str(e),
                        **context,
                        exc_info=True,
                    )

        except TimeoutError:
            logger.error(
                "Publication timeout exceeded",
                timeout=timeout,
                **context,
            )

    async def publish_entity_changed(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        data: dict[str, Any] | None = None,
        send_to_redis: bool = True,
        send_to_mqtt: bool = False,
        db: AsyncSession | None = None,
    ) -> None:
        """Опубликовать событие изменения сущности.

        Args:
            entity_type: Тип сущности (vehicle, work_regime, status, etc.)
            entity_id: ID сущности
            action: Действие (create, update, delete)
            data: Дополнительные данные
            send_to_redis: Флаг отправки в Redis
            send_to_mqtt: Флаг отправки в MQTT
            db: Сессия базы данных (требуется для MQTT)
        """
        # Валидация входных данных
        if not entity_type or entity_type == "unknown":
            logger.warning(
                "Skipping event publication: invalid entity_type",
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
            )
            return

        if not entity_id or entity_id == "unknown" or entity_id is None:
            logger.warning(
                "Skipping event publication: invalid entity_id",
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
            )
            return

        context = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
        }

        # Создаем payload события
        payload = self._create_event_payload(
            event_type="entity_changed",
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
        )

        # Проверяем, что payload не содержит None значений
        if None in payload.values():
            logger.warning(
                "Skipping event publication: payload contains None values",
                payload=payload,
                **context,
            )
            return

        # Подготавливаем задачи для параллельного выполнения
        publish_tasks = []

        if send_to_redis:
            redis_task = asyncio.create_task(
                self._publish_to_redis(
                    channel=self.config.redis_channel,
                    payload=payload,
                    context=context,
                ),
            )
            publish_tasks.append(redis_task)

        if send_to_mqtt:
            if not db:
                logger.warning(
                    "Skipping MQTT publish: database session not provided",
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
            else:
                await self._publish_to_mqtt(
                    channel=self.config.mqtt_channel,
                    payload=payload,
                    context=context,
                    db=db,
                )
            # publish_tasks.append(mqtt_task)

        # Выполняем публикации параллельно
        await self._publish_parallel(publish_tasks, context)
