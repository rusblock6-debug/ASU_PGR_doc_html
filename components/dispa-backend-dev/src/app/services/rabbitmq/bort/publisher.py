"""RabbitMQ publisher для bort-режима."""

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


class VehiclePublisherBortManager(ABSPublisherManager):
    """Publisher manager для отправки сообщений в bort-режиме."""

    def __init__(self, vehicle_id: str | int) -> None:
        self.vehicle_id = vehicle_id
        self.queue = RabbitQueue(f"bort_{self.vehicle_id}.server.trip.src")

    async def task_publish(self, message: BaseMsgScheme, vehicle_id: int | None = None) -> None:
        """Опубликовать сообщение задания в очередь борта."""
        await broker.connect()
        await broker.publish(message.model_dump(), self.queue)
        logger.info(
            "Опубликовано сообщение",
            source="bort",
            queue=self.queue,
            type=message.message_data.message_type,
            event=message.message_data.message_event,
        )

    async def success_publish(self, message: dict[str, Any], vehicle_id: int | None = None) -> None:
        """Опубликовать сообщение о подтверждении доставки."""
        await broker.connect()
        await broker.publish(message, self.queue)
        logger.info(
            "Опубликовано сообщение о подтверждении доставки",
            source="bort",
            queue=self.queue,
            message_id=message.get("id"),
        )
