"""Менеджер публикации сообщений на борт через RabbitMQ."""

from typing import Any

from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitQueue

from app.core.config import settings
from app.services.rabbitmq.config.base_publisher import ABSPublisherManager
from app.services.rabbitmq.config.logger import get_logger
from app.services.rabbitmq.schemas import BaseMsgScheme

logger = get_logger()

broker = RabbitBroker(settings.rabbit.url)
app = FastStream(broker)


class ServerPublisherBortManager(ABSPublisherManager):
    """Менеджер публикации сообщений на борт."""

    async def task_publish(self, message: BaseMsgScheme, vehicle_id: int | None = None) -> None:
        """Публикация сообщения задания на борт."""
        queue = RabbitQueue(f"server.bort_{vehicle_id}.trip.src")
        await broker.connect()
        await broker.publish(message.model_dump(), queue)
        logger.info(
            "Опубликовано сообщение",
            source="server",
            queue=queue,
            type=message.message_data.message_type,
            event=message.message_data.message_event,
        )

    async def success_publish(self, message: dict[str, Any], vehicle_id: int | None = None) -> None:
        """Публикация подтверждения доставки на борт."""
        queue = RabbitQueue(f"server.bort_{vehicle_id}.trip.src")
        await broker.connect()
        await broker.publish(message, queue)
        logger.info(
            "Опубликовано сообщение о подтверждении доставки",
            source="server",
            queue=queue,
            message_id=message.get("id"),
        )
