"""MQTT Client для подписки на события от eKuiper через Nanomq.

Подписывается на топики датчиков и передает события в State Machine.
"""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

from gmqtt import Client as MQTTClient
from loguru import logger


class TripServiceMQTTClient:
    """MQTT клиент для Trip Service.

    Подписывается на топики событий от eKuiper и передает их в State Machine.
    """

    def __init__(
        self,
        vehicle_id: int | str,
        host: str = "nanomq",
        port: int = 1883,
        event_handler: Callable[[str, dict[str, Any]], Awaitable[None]] | None = None,
    ):
        """Инициализация MQTT клиента.

        Args:
            vehicle_id: ID машины (AC9)
            host: Хост Nanomq
            port: Порт Nanomq
            event_handler: Async функция для обработки событий
        """
        vehicle_id_str = str(vehicle_id)
        self.vehicle_id = vehicle_id_str
        self.host = host
        self.port = port
        self.event_handler = event_handler

        # Создаем MQTT клиент
        if vehicle_id_str == "+":
            client_id = "trip-service-server"
        else:
            # Валидация: заменяем недопустимые символы в client_id
            safe_vehicle_id = vehicle_id_str.replace("+", "_plus_").replace("#", "_hash_").replace("/", "_")
            client_id = f"trip-service-{safe_vehicle_id}"

        self.client = MQTTClient(client_id)

        # Настраиваем callback для событий
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.on_subscribe = self._on_subscribe

        self._connected = False
        # ВАЖНО: eKuiper публикует в топики БЕЗ слэша в начале и в /events топики
        # Используем vehicle_id из настроек для MQTT топиков от eKuiper
        from app.core.config import settings

        vehicle_id = str(settings.vehicle_id)
        self._topics = [
            f"truck/{vehicle_id}/sensor/tag/events",
            f"truck/{vehicle_id}/sensor/speed/events",
            f"truck/{vehicle_id}/sensor/weight/events",
            f"truck/{vehicle_id}/sensor/vibro/events",
            f"truck/{vehicle_id}/sensor/fuel/events",
            f"truck/{vehicle_id}/sensor/wifi/fake_events",
            f"dispatcher/{vehicle_id}/changes",
        ]

        # Дополнительный топик для enterprise-service (только в бортовом режиме)
        self.service_mode = settings.service_mode

        logger.info(
            "MQTT client initialized",
            vehicle_id=vehicle_id,
            client_id=client_id,
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

        if self.service_mode == "bort":
            # Bort Mode: подписываемся на датчики от eKuiper
            for topic in self._topics:
                client.subscribe(topic, qos=1)
                logger.info("Subscribed to MQTT topic (bort mode)", topic=topic)

            # Bort Mode: подписываемся на enterprise-service события
            # Enterprise-service (на сервере) публикует в серверный MQTT,
            # события приходят через MQTT bridge на бортовой MQTT
            enterprise_topic = f"truck/{self.vehicle_id}/enterprise-service/events"
            client.subscribe(enterprise_topic, qos=1)
            logger.info("Subscribed to enterprise-service topic (bort mode)", topic=enterprise_topic)

        elif self.service_mode == "server":
            # Server Mode: подписываемся на события от ВСЕХ бортов (wildcard +)
            trip_service_events_topic = "truck/+/trip-service/events"
            client.subscribe(trip_service_events_topic, qos=1)
            logger.info(
                "Subscribed to trip-service events from all vehicles (server mode)",
                topic=trip_service_events_topic,
            )

        else:
            logger.warning("Unknown service_mode, no MQTT subscriptions", service_mode=self.service_mode)

    def _on_disconnect(self, client: Any, packet: Any, exc: Any = None) -> None:
        """Callback при отключении от брокера."""
        logger.warning("MQTT disconnected", exception=str(exc) if exc else None)
        self._connected = False

    def _on_subscribe(self, client: Any, mid: Any, qos: Any, properties: Any) -> None:
        """Callback при успешной подписке."""
        logger.info("MQTT subscription confirmed", mid=mid, qos=qos)

    def _on_message(self, client: Any, topic: str, payload: bytes, qos: int, properties: Any) -> None:
        """Callback при получении сообщения из MQTT.

        Парсит JSON payload и вызывает event_handler.
        """
        try:
            # Декодируем payload
            message = payload.decode("utf-8")

            # ВАЖНО: Логируем ВСЕ сообщения из trip-service/events для серверного режима
            # чтобы видеть, получаем ли мы сообщения с place_remaining_change
            if "trip-service/events" in topic:
                # Проверяем наличие place_remaining_change в raw строке ДО парсинга
                has_prc_in_raw = "place_remaining_change" in message

                logger.info(
                    "📨 [SERVER] MQTT raw payload received (trip-service)",
                    topic=topic,
                    payload_size=len(message),
                    payload_preview=message[:500] if len(message) > 500 else message,
                    has_place_remaining_change_in_raw=has_prc_in_raw,
                    payload_full=message,  # Всегда логируем полный payload для trip-service
                    qos=qos,
                )

                # Если есть place_remaining_change в raw, логируем отдельно
                if has_prc_in_raw:
                    logger.warning(
                        "✅ [SERVER] FOUND place_remaining_change in raw payload!",
                        topic=topic,
                        payload_size=len(message),
                        payload_full=message,
                    )

            # Детальное логирование raw payload для trip-service событий ДО парсинга (серверный режим)
            if "trip-service/events" in topic:
                logger.info(
                    "📨 [SERVER] MQTT raw payload received (trip-service)",
                    topic=topic,
                    payload_size=len(message),
                    payload_preview=message[:500] if len(message) > 500 else message,
                    has_place_remaining_change_in_raw="place_remaining_change" in message,
                    payload_full=message if len(message) < 1000 else None,
                )

            data = json.loads(message)

            # Логируем для trip-service событий, чтобы видеть place_remaining_change
            if "trip-service/events" in topic:
                logger.info(
                    "📨 [SERVER] MQTT message parsed (trip-service)",
                    topic=topic,
                    payload_size=len(message),
                    event_type=data.get("event_type"),
                    has_place_remaining_change="place_remaining_change" in data,
                    place_remaining_change=data.get("place_remaining_change"),
                    task_id=data.get("task_id"),
                    data_keys=list(data.keys()) if isinstance(data, dict) else None,
                    data_full=data if len(str(data)) < 1000 else None,
                )
            else:
                logger.debug(
                    "📨 MQTT message received",
                    topic=topic,
                    payload_size=len(message),
                )

            # Вызываем обработчик событий асинхронно
            if self.event_handler:
                asyncio.ensure_future(self.event_handler(topic, data))

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
        if not self._connected:
            logger.error(
                "MQTT publish: client is disconnected, trying to reconnect",
                topic=topic,
                host=self.host,
                port=self.port,
            )
            try:
                await self.connect()
            except Exception as reconnect_error:
                logger.error(
                    "MQTT publish skipped: reconnect failed",
                    topic=topic,
                    error=str(reconnect_error),
                )
                return
        try:
            # Детальное логирование для trip-service событий ПЕРЕД сериализацией
            if "trip-service/events" in topic:
                logger.info(
                    "📤 [BORT] MQTT publish: data before serialization",
                    topic=topic,
                    event_type=data.get("event_type") if isinstance(data, dict) else None,
                    has_place_remaining_change="place_remaining_change" in data if isinstance(data, dict) else False,
                    place_remaining_change=data.get("place_remaining_change") if isinstance(data, dict) else None,
                    data_keys=list(data.keys()) if isinstance(data, dict) else None,
                    data_full=data,
                )

            payload = json.dumps(data)

            # Логируем после сериализации для trip-service событий
            if "trip-service/events" in topic:
                logger.info(
                    "📤 [BORT] MQTT publish: payload after serialization",
                    topic=topic,
                    payload_size=len(payload),
                    payload_preview=payload[:500] if len(payload) > 500 else payload,
                    has_place_remaining_change_in_payload="place_remaining_change" in payload,
                    payload_full=payload if len(payload) < 1000 else None,
                )

            # НЕ сохраняем сообщения (retain=False) для trip events
            # Клиенты должны получать только актуальные события
            self.client.publish(topic, payload, qos=1, retain=False)

            if "trip-service/events" not in topic:
                logger.info(
                    "📤 MQTT message published",
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
