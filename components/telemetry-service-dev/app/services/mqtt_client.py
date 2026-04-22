"""
MQTT Client для подписки на телеметрию с серверного NanoMQ брокера.

Подписывается на топики событий датчиков и передает их в Redis Streams.
"""
import asyncio
import json
import re
from typing import Optional, Callable, Awaitable
from gmqtt import Client as MQTTClient
from loguru import logger
from app.core.config import settings


class TelemetryMQTTClient:
    """
    MQTT клиент для Telemetry Service.
    
    Подписывается на топики событий датчиков (/events) и downsampled данных (/ds)
    и передает их в Redis Streams.
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        message_handler: Optional[Callable[[str, str, dict], Awaitable[None]]] = None
    ):
        """
        Инициализация MQTT клиента.
        
        Args:
            host: Хост NanoMQ брокера
            port: Порт NanoMQ брокера
            message_handler: Async функция для обработки сообщений (vehicle_id, sensor_type, data)
        """
        self.host = host
        self.port = port
        self.message_handler = message_handler
        
        # Создаем MQTT клиент с уникальным ID
        self.client = MQTTClient("telemetry-service")
        
        # Настраиваем callback для событий
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.on_subscribe = self._on_subscribe
        
        self._connected = False
        
        # Топики для подписки: truck/+/sensor/+/events и truck/+/sensor/+/ds
        # Примеры: truck/AC9/sensor/speed/events, truck/AC9/sensor/speed/ds
        self._topic_patterns = [
            "truck/+/sensor/+/events",
            "truck/+/sensor/+/ds"
        ]
        
        logger.info(
            "Telemetry MQTT client initialized",
            host=host,
            port=port,
            topic_patterns=self._topic_patterns
        )
    
    async def connect(self) -> None:
        """Подключение к NanoMQ брокеру"""
        try:
            logger.info(
                "Connecting to MQTT broker",
                host=self.host,
                port=self.port
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
                exc_info=True
            )
            raise
    
    async def disconnect(self) -> None:
        """Отключение от NanoMQ брокера"""
        try:
            if self._connected:
                await self.client.disconnect()
                self._connected = False
                logger.info("Disconnected from MQTT broker")
        except Exception as e:
            logger.error(
                "Error disconnecting from MQTT broker",
                error=str(e)
            )
    
    def _on_connect(self, client, flags, rc, properties):
        """Callback при подключении к брокеру"""
        logger.info("MQTT connected", return_code=rc)
        
        # Подписываемся на все топики с wildcard
        for topic_pattern in self._topic_patterns:
            client.subscribe(topic_pattern, qos=0)
            logger.info("Subscribed to MQTT topic", topic=topic_pattern)
    
    def _on_disconnect(self, client, packet, exc=None):
        """Callback при отключении от брокера"""
        logger.warning("MQTT disconnected", exception=str(exc) if exc else None)
        self._connected = False
    
    def _on_subscribe(self, client, mid, qos, properties):
        """Callback при успешной подписке"""
        logger.info("MQTT subscription confirmed", mid=mid, qos=qos)
    
    def _parse_topic(self, topic: str) -> tuple[Optional[str], Optional[str]]:
        """
        Парсинг топика для извлечения vehicle_id и sensor_type.
        
        Формат топика: truck/{vehicle_id}/sensor/{sensor_type}/{suffix}
        Поддерживает суффиксы: events, ds
        
        Args:
            topic: MQTT топик
            
        Returns:
            Tuple (vehicle_id, sensor_type) или (None, None) при ошибке парсинга
        """
        # Регулярное выражение для парсинга: truck/{vehicle_id}/sensor/{sensor_type}/{events|ds}
        pattern = r"truck/([^/]+)/sensor/([^/]+)/(events|ds)"
        match = re.match(pattern, topic)
        
        if match:
            vehicle_id = match.group(1)
            sensor_type = match.group(2)
            suffix = match.group(3)  # events или ds
            logger.debug("Topic parsed successfully", topic=topic, suffix=suffix)
            return vehicle_id, sensor_type
        
        logger.warning("Failed to parse topic", topic=topic)
        return None, None
    
    def _on_message(self, client, topic, payload, qos, properties):
        """
        Callback при получении сообщения из MQTT.
        
        Парсит топик, извлекает vehicle_id и sensor_type,
        парсит JSON payload и вызывает message_handler.
        """
        try:
            # Парсим топик для извлечения vehicle_id и sensor_type
            vehicle_id, sensor_type = self._parse_topic(topic)
            
            if not vehicle_id or not sensor_type:
                logger.warning("Skipping message - failed to parse topic", topic=topic)
                return
            
            # Декодируем payload
            message = payload.decode('utf-8')
            data = json.loads(message)
            
            logger.debug(
                "MQTT message received",
                topic=topic,
                vehicle_id=vehicle_id,
                sensor_type=sensor_type,
                payload_size=len(message)
            )
            
            # Вызываем обработчик сообщений асинхронно
            if self.message_handler:
                asyncio.create_task(self.message_handler(vehicle_id, sensor_type, data))
            
        except json.JSONDecodeError as e:
            # Проверяем, является ли это проблемой eKuiper с <no value>
            if b"<no value>" in payload:
                logger.debug(
                    "Skipping message with <no value> from eKuiper",
                    topic=topic
                )
            else:
                logger.error(
                    "Failed to parse MQTT message JSON",
                    topic=topic,
                    payload=payload[:100] if payload else None,
                    error=str(e)
                )
        except Exception as e:
            logger.error(
                "Error handling MQTT message",
                topic=topic,
                error=str(e),
                exc_info=True
            )
    
    def is_connected(self) -> bool:
        """Проверка состояния подключения"""
        return self._connected

