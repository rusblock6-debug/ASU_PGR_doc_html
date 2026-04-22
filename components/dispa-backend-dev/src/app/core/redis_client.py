"""Redis клиент для Trip Service.

Используется для:
- State management (текущее состояние State Machine)
- Pub/Sub уведомления об изменениях состояния
- Кэширование данных
"""

import json
from datetime import datetime
from typing import Any

import redis.asyncio as redis
from loguru import logger

from app.core.config import settings


class RedisClient:
    """Async Redis клиент с поддержкой Pub/Sub."""

    def __init__(self) -> None:
        self.redis: redis.Redis | None = None
        self.pubsub: redis.client.PubSub | None = None

    async def connect(self) -> None:
        """Подключение к Redis."""
        try:
            self.redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
            )
            # Проверка подключения
            await self.redis.ping()  # type: ignore[misc]
            logger.info("Redis connected successfully", redis_url=settings.redis_url)

        except Exception as e:
            logger.error("Redis connection failed", error=str(e), exc_info=True)
            raise

    async def disconnect(self) -> None:
        """Отключение от Redis."""
        try:
            if self.pubsub:
                await self.pubsub.close()

            if self.redis:
                await self.redis.close()

            logger.info("Redis disconnected successfully")

        except Exception as e:
            logger.error("Redis disconnection error", error=str(e))

    async def get(self, key: str) -> str | None:
        """Получить значение по ключу."""
        try:
            if self.redis is None:
                raise RuntimeError("Redis не подключен")
            value = await self.redis.get(key)
            return value

        except Exception as e:
            logger.error("Redis GET error", key=key, error=str(e))
            return None

    async def get_json(self, key: str) -> dict[str, Any] | None:
        """Получить JSON значение по ключу."""
        try:
            if self.redis is None:
                raise RuntimeError("Redis не подключен")
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None

        except Exception as e:
            logger.error("Redis GET JSON error", key=key, error=str(e))
            return None

    async def set(
        self,
        key: str,
        value: str,
        ex: int | None = None,
    ) -> bool:
        """Установить значение по ключу.

        Args:
            key: Redis ключ
            value: Значение
            ex: TTL в секундах (опционально)
        """
        try:
            if self.redis is None:
                raise RuntimeError("Redis не подключен")
            await self.redis.set(key, value, ex=ex)
            return True

        except Exception as e:
            logger.error("Redis SET error", key=key, error=str(e))
            return False

    async def set_if_not_exists(
        self,
        key: str,
        value: str,
        ex: int | None = None,
    ) -> bool:
        """Установить значение только если ключ не существует (SET NX)."""
        try:
            if self.redis is None:
                raise RuntimeError("Redis не подключен")
            return bool(await self.redis.set(key, value, ex=ex, nx=True))

        except Exception as e:
            logger.error("Redis SET NX error", key=key, error=str(e))
            return False

    async def set_json(
        self,
        key: str,
        value: dict[str, Any],
        ex: int | None = None,
    ) -> bool:
        """Установить JSON значение по ключу.

        Args:
            key: Redis ключ
            value: JSON значение
            ex: TTL в секундах (опционально)
        """
        try:
            json_value = json.dumps(value, default=str)
            if self.redis is None:
                raise RuntimeError("Redis не подключен")
            await self.redis.set(key, json_value, ex=ex)
            return True

        except Exception as e:
            logger.error("Redis SET JSON error", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Удалить ключ."""
        try:
            if self.redis is None:
                raise RuntimeError("Redis не подключен")
            await self.redis.delete(key)
            return True

        except Exception as e:
            logger.error("Redis DELETE error", key=key, error=str(e))
            return False

    async def publish(self, channel: str, message: dict[str, Any]) -> bool:
        """Опубликовать сообщение в канал Pub/Sub.

        Format: trip-service:vehicle:{vehicle_id}:changes

        Args:
            channel: Канал для публикации
            message: Сообщение в формате dict
        """
        try:
            json_message = json.dumps(message, default=str)
            if self.redis is None:
                raise RuntimeError("Redis не подключен")
            await self.redis.publish(channel, json_message)
            logger.debug("Redis message published", channel=channel)
            return True

        except Exception as e:
            logger.error("Redis PUBLISH error", channel=channel, error=str(e))
            return False

    async def get_state_machine_data(self, vehicle_id: str) -> dict[str, Any] | None:
        """Получить текущее состояние State Machine для vehicle.

        Redis key format: trip-service:vehicle:{vehicle_id}:state
        """
        key = f"trip-service:vehicle:{vehicle_id}:state"
        return await self.get_json(key)

    async def set_state_machine_data(
        self,
        vehicle_id: str,
        state_data: dict[str, Any],
    ) -> bool:
        """Сохранить текущее состояние State Machine для vehicle.

        Redis key format: trip-service:vehicle:{vehicle_id}:state

        После сохранения публикует уведомление в Pub/Sub канал.
        """
        key = f"trip-service:vehicle:{vehicle_id}:state"
        channel = f"trip-service:vehicle:{vehicle_id}:changes"

        # Сохраняем состояние
        success = await self.set_json(key, state_data)

        if success:
            # Публикуем уведомление об изменении
            await self.publish(channel, state_data)
            logger.info(
                "State machine data updated",
                vehicle_id=vehicle_id,
                state=state_data.get("state"),
            )

        return success

    # === Active Trip Management ===

    async def set_active_trip(self, vehicle_id: str, trip_data: dict[str, Any]) -> bool:
        """Сохранить данные активного рейса.

        Redis key: trip-service:vehicle:{vehicle_id}:active_trip
        Pub/Sub: trip-service:vehicle:{vehicle_id}:active_trip:changes
        """
        key = f"trip-service:vehicle:{vehicle_id}:active_trip"
        channel = f"{key}:changes"

        success = await self.set_json(key, trip_data)
        if success:
            await self.publish(channel, trip_data)
        return success

    async def get_active_trip(self, vehicle_id: str) -> dict[str, Any] | None:
        """Получить данные активного рейса."""
        key = f"trip-service:vehicle:{vehicle_id}:active_trip"
        return await self.get_json(key)

    async def delete_active_trip(self, vehicle_id: str) -> bool:
        """Удалить данные активного рейса."""
        key = f"trip-service:vehicle:{vehicle_id}:active_trip"
        channel = f"{key}:changes"

        success = await self.delete(key)
        if success:
            await self.publish(channel, {"active_trip": None, "deleted": True})
        return success

    # === Active Task Management ===

    async def set_active_task(self, vehicle_id: str, task_data: dict[str, Any]) -> bool:
        """Сохранить данные активного задания.

        Redis key: trip-service:vehicle:{vehicle_id}:active_task
        Pub/Sub: trip-service:vehicle:{vehicle_id}:active_task:changes
        """
        key = f"trip-service:vehicle:{vehicle_id}:active_task"
        channel = f"{key}:changes"

        success = await self.set_json(key, task_data)
        if success:
            await self.publish(channel, task_data)
        return success

    async def get_active_task(self, vehicle_id: str) -> dict[str, Any] | None:
        """Получить данные активного задания."""
        key = f"trip-service:vehicle:{vehicle_id}:active_task"
        return await self.get_json(key)

    async def delete_active_task(self, vehicle_id: str) -> bool:
        """Удалить данные активного задания."""
        key = f"trip-service:vehicle:{vehicle_id}:active_task"
        channel = f"{key}:changes"

        success = await self.delete(key)
        if success:
            await self.publish(channel, {"active_task": None, "deleted": True})
        return success

    # === Redis Streams для Tag History ===

    async def add_tag_to_history(
        self,
        vehicle_id: str,
        point_id: str,
        tag: str,
        extra_data: dict[str, Any] | None = None,
    ) -> bool:
        """Добавить метку в историю (Redis Stream).

        Stream key: trip-service:vehicle:{vehicle_id}:tag_history
        Pub/Sub: trip-service:vehicle:{vehicle_id}:tag_history:changes
        """
        try:
            stream_key = f"trip-service:vehicle:{vehicle_id}:tag_history"
            channel = f"{stream_key}:changes"

            entry: dict[str, str] = {
                "point_id": point_id,
                "tag": tag,
                "timestamp": json.dumps(
                    {"$date": datetime.utcnow().isoformat()},
                    default=str,
                ),
                "extra_data": json.dumps(extra_data or {}, default=str),
            }

            if self.redis is None:
                raise RuntimeError("Redis не подключен")
            await self.redis.xadd(stream_key, entry)  # type: ignore[arg-type]

            # Публиковать изменение
            await self.publish(channel, {"point_id": point_id, "tag": tag})

            return True

        except Exception as e:
            logger.error("Failed to add tag to history", vehicle_id=vehicle_id, error=str(e))
            return False

    async def get_tag_history(self, vehicle_id: str) -> list[dict[str, Any]]:
        """Получить всю историю меток из Redis Stream."""
        try:
            stream_key = f"trip-service:vehicle:{vehicle_id}:tag_history"
            if self.redis is None:
                raise RuntimeError("Redis не подключен")
            entries = await self.redis.xread({stream_key: "0"}, count=1000)

            if not entries:
                return []

            # Парсинг результата: [(stream_key, [(entry_id, data), ...])]
            history: list[dict[str, Any]] = []
            for _, stream_entries in entries:
                for _, data in stream_entries:
                    history.append(
                        {
                            "point_id": data.get("point_id"),
                            "tag": data.get("tag"),
                            "timestamp": json.loads(data.get("timestamp", "{}")).get("$date"),
                            "extra_data": json.loads(data.get("extra_data", "{}")),
                        },
                    )

            return history

        except Exception as e:
            logger.error("Failed to get tag history", vehicle_id=vehicle_id, error=str(e))
            return []

    async def clear_tag_history(self, vehicle_id: str) -> bool:
        """Очистить историю меток (удалить Stream)."""
        try:
            stream_key = f"trip-service:vehicle:{vehicle_id}:tag_history"
            if self.redis is None:
                raise RuntimeError("Redis не подключен")
            await self.redis.delete(stream_key)
            return True

        except Exception as e:
            logger.error("Failed to clear tag history", vehicle_id=vehicle_id, error=str(e))
            return False

    # === Redis Sorted Sets для Task Queue ===

    async def add_task_to_queue(
        self,
        vehicle_id: str,
        task_id: str,
        order: int,
        start_point_id: str,
    ) -> bool:
        """Добавить задание в очередь (Sorted Sets).

        Keys:
        - trip-service:vehicle:{vehicle_id}:task_queue:ordered (score = order)
        - trip-service:vehicle:{vehicle_id}:task_queue:{start_point_id} (score = order)
        """
        try:
            ordered_key = f"trip-service:vehicle:{vehicle_id}:task_queue:ordered"
            point_key = f"trip-service:vehicle:{vehicle_id}:task_queue:{start_point_id}"

            if self.redis is None:
                raise RuntimeError("Redis не подключен")
            await self.redis.zadd(ordered_key, {task_id: order})
            await self.redis.zadd(point_key, {task_id: order})

            return True

        except Exception as e:
            logger.error("Failed to add task to queue", task_id=task_id, error=str(e))
            return False

    async def get_next_task_by_order(self, vehicle_id: str) -> str | None:
        """Получить первое задание по order из общей очереди."""
        try:
            key = f"trip-service:vehicle:{vehicle_id}:task_queue:ordered"
            if self.redis is None:
                raise RuntimeError("Redis не подключен")
            tasks = await self.redis.zrange(key, 0, 0)

            if tasks:
                return tasks[0]
            return None

        except Exception as e:
            logger.error("Failed to get next task by order", error=str(e))
            return None

    async def get_next_task_by_point(
        self,
        vehicle_id: str,
        point_id: str,
    ) -> str | None:
        """Получить первое задание из очереди для конкретной точки."""
        try:
            key = f"trip-service:vehicle:{vehicle_id}:task_queue:{point_id}"
            if self.redis is None:
                raise RuntimeError("Redis не подключен")
            tasks = await self.redis.zrange(key, 0, 0)

            if tasks:
                return tasks[0]
            return None

        except Exception as e:
            logger.error("Failed to get next task by point", error=str(e))
            return None

    async def remove_task_from_queue(self, vehicle_id: str, task_id: str) -> bool:
        """Удалить задание из всех очередей."""
        try:
            # Удалить из общей очереди
            ordered_key = f"trip-service:vehicle:{vehicle_id}:task_queue:ordered"
            if self.redis is None:
                raise RuntimeError("Redis не подключен")
            await self.redis.zrem(ordered_key, task_id)

            # Удалить из всех очередей по точкам (используем pattern)
            point_pattern = f"trip-service:vehicle:{vehicle_id}:task_queue:*"
            point_keys = await self.redis.keys(point_pattern)

            for key in point_keys:
                if key != ordered_key:  # Не удалять дважды
                    await self.redis.zrem(key, task_id)

            return True

        except Exception as e:
            logger.error("Failed to remove task from queue", task_id=task_id, error=str(e))
            return False

    # === Trip Events для real-time обновлений ===

    async def publish_trip_event(
        self,
        event_type: str,
        trip_data: dict[str, Any],
        page: int | None = None,
    ) -> bool:
        """Опубликовать событие изменения рейса.

        Pub/Sub канал: trip-service:trips:changes

        Args:
            event_type: Тип события (created, updated, deleted)
            trip_data: Данные рейса (полный объект для created/updated, только id для deleted)
            page: Номер страницы пагинации (опционально, для контекста)
        """
        channel = "trip-service:trips:changes"

        message: dict[str, Any] = {
            "event_type": event_type,
            "trip": trip_data,
            "page": page,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return await self.publish(channel, message)


# Глобальный экземпляр Redis клиента
redis_client: RedisClient = RedisClient()
