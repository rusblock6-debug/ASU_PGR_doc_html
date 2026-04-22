"""EventPublisher - публикация событий изменений сущностей в MQTT.
Используется в серверном режиме для уведомления бортов об изменениях графа.
"""

import json
from datetime import datetime
from typing import Any

from loguru import logger

from config.settings import get_settings

settings = get_settings()


class EventPublisher:
    """Публикатор событий для уведомления бортов об изменениях в графе.

    В серверном режиме публикует в wildcard топик truck/+/graph-service/events (broadcast).
    В бортовом режиме публикация отключена.
    """

    def _create_event_payload(
        self,
        event_type: str,
        entity_type: str,
        entity_id: Any,
        action: str,
        data: dict | None = None,
    ) -> dict[str, Any]:
        """Создание payload события.

        data всегда пустая - борт должен делать GET запрос для получения актуальных данных.
        """
        payload = {
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {},  # Всегда пустая - борт делает GET запрос
        }
        return payload

    async def publish_entity_changed(
        self,
        entity_type: str,
        entity_id: Any,
        action: str,
        data: dict | None = None,
    ) -> bool:
        """Опубликовать событие изменения сущности.

        Args:
            entity_type: Тип сущности (horizon, node, edge, tag, place, shaft)
            entity_id: ID сущности
            action: Действие (create, update, delete)
            data: Игнорируется - всегда пустая. Борт должен делать GET запрос для получения данных.

        Returns:
            True если событие опубликовано успешно
        """
        # Проверяем режим работы
        if not settings.is_server_mode:
            return False

        # Валидация
        if not entity_type or not entity_id:
            logger.warning(
                "Skipping MQTT publish: invalid entity data",
                entity_type=entity_type,
                entity_id=entity_id,
            )
            return False

        # Создаем payload (data всегда пустая - борт делает GET запрос)
        payload = self._create_event_payload(
            event_type="entity_changed",
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
        )

        # В серверном режиме публикуем в общий топик без wildcards (борты подписываются на него)
        topic = "graph-service/events"

        try:
            import aiomqtt

            async with aiomqtt.Client(
                hostname=settings.nanomq_host,
                port=settings.nanomq_mqtt_port,
            ) as client:
                await client.publish(
                    topic,
                    json.dumps(payload),
                    qos=1,
                )
                logger.info(
                    f"[MQTT] Event published to {topic}",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    action=action,
                )
                return True

        except ImportError:
            logger.warning("aiomqtt not installed, MQTT publishing disabled")
            return False
        except Exception as e:
            logger.error(
                f"[ERROR] Failed to publish event to MQTT: {e}",
                exc_info=True,
            )
            return False


# Глобальный экземпляр
event_publisher = EventPublisher()
