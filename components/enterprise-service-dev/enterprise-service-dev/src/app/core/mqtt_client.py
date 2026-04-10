"""MQTT Client для подписки на события от eKuiper через Nanomq.

Подписывается на топики датчиков и передает события в State Machine.
"""

import asyncio
import json
from collections.abc import Callable, Coroutine
from typing import Any

from gmqtt import Client as MQTTClient
from loguru import logger


class EnterpriseServiceMQTTClient:
    """MQTT клиент для Enterprise Service.

    Подписывается на топики событий от eKuiper и передает их в State Machine.
    """

    def __init__(
        self,
        vehicle_id: str,
        host: str = "nanomq-server",
        port: int = 1883,
        event_handler: Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]] | None = None,
    ):
        """Инициализация MQTT клиента.

        Args:
            vehicle_id: ID машины (AC9)
            host: Хост Nanomq
            port: Порт Nanomq
            event_handler: Async функция для обработки событий
        """
        self.vehicle_id = vehicle_id
        self.truck_id = vehicle_id  # Для совместимости с топиками
        self.host = host
        self.port = port
        self.event_handler = event_handler

        # Создаем MQTT клиент
        self.client = MQTTClient(f"enterprise-service-{vehicle_id}")

        # Настраиваем callback для событий
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.on_subscribe = self._on_subscribe

        self._connected = False
        # ВАЖНО: eKuiper публикует в топики БЕЗ слэша в начале и в /events топики
        # Используем truck_id из настроек для MQTT топиков от eKuiper

        self._topics = [
            f"truck/{self.truck_id}/enterprise-service/events",
        ]

        logger.info(
            "MQTT client initialized",
            vehicle_id=vehicle_id,
            host=host,
            port=port,
            topics=self._topics,
        )

    async def connect(self) -> None:
        """Подключение к Nanomq брокеру."""
        try:
            logger.info(
                "Connecting to MQTT broker",
                host=self.host,
                port=self.port,
            )

            await self.client.connect(self.host, self.port)
            self._connected = True

            logger.info("Connected to MQTT broker successfully")

        except Exception as e:
            logger.error(
                "Failed to connect to MQTT broker",
                host=self.host,
                port=self.port,
                error=str(e),
                exc_info=True,
            )
            raise

    async def disconnect(self) -> None:
        """Отключение от Nanomq брокера."""
        try:
            if self._connected:
                await self.client.disconnect()
                self._connected = False
                logger.info("Disconnected from MQTT broker")
        except Exception as e:
            logger.error(
                "Error disconnecting from MQTT broker",
                error=str(e),
            )

    def _on_connect(self, client: Any, flags: Any, rc: Any, properties: Any) -> None:
        """Callback при подключении к брокеру."""
        logger.info("MQTT connected", return_code=rc)

        # Подписываемся на топики
        for topic in self._topics:
            client.subscribe(topic, qos=1)
            logger.info("Subscribed to MQTT topic", topic=topic)

    def _on_disconnect(self, client: Any, packet: Any, exc: Any = None) -> None:
        """Callback при отключении от брокера."""
        logger.warning("MQTT disconnected", exception=str(exc) if exc else None)
        self._connected = False

    def _on_subscribe(self, client: Any, mid: Any, qos: Any, properties: Any) -> None:
        """Callback при успешной подписке."""
        logger.info("MQTT subscription confirmed", mid=mid, qos=qos)

    def _on_message(
        self,
        client: Any,
        topic: str,
        payload: bytes,
        qos: int,
        properties: Any,
    ) -> None:
        """Callback при получении сообщения из MQTT.

        Парсит JSON payload и вызывает event_handler.
        """
        try:
            # Декодируем payload
            message = payload.decode("utf-8")
            data = json.loads(message)

            logger.debug(
                "MQTT message received",
                topic=topic,
                payload_size=len(message),
            )

            # Вызываем обработчик событий асинхронно
            if self.event_handler:
                asyncio.create_task(self.event_handler(topic, data))

        except json.JSONDecodeError as e:
            # Проверяем, является ли это проблемой eKuiper с <no value>
            if b"<no value>" in payload:
                logger.debug(
                    "Skipping message with <no value> from eKuiper",
                    topic=topic,
                )
            else:
                logger.error(
                    "Failed to parse MQTT message JSON",
                    topic=topic,
                    payload=payload[:100],
                    error=str(e),
                )
        except Exception as e:
            logger.error(
                "Error handling MQTT message",
                topic=topic,
                error=str(e),
                exc_info=True,
            )

    async def publish(self, topic: str, data: dict[str, Any]) -> None:
        """Публикация события в MQTT топик.

        Args:
            topic: MQTT топик
            data: Данные для публикации
        """
        try:
            payload = json.dumps(data)
            self.client.publish(topic, payload, qos=1, retain=False)

            logger.debug(
                "MQTT message published",
                topic=topic,
                payload_size=len(payload),
            )

        except Exception as e:
            logger.error(
                "Failed to publish MQTT message",
                topic=topic,
                error=str(e),
            )

    def is_connected(self) -> bool:
        """Проверка состояния подключения."""
        return self._connected
