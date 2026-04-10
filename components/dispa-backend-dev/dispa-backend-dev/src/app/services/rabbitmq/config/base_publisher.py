"""Базовый абстрактный класс publisher manager для RabbitMQ."""

from abc import ABC, abstractmethod
from typing import Any

from app.services.rabbitmq.schemas import BaseMsgScheme


class ABSPublisherManager(ABC):
    """Абстрактный базовый класс для управления публикацией сообщений RabbitMQ."""

    @abstractmethod
    async def task_publish(self, message: BaseMsgScheme, vehicle_id: int | None = None) -> None:
        """Опубликовать сообщение задания."""
        raise NotImplementedError

    @abstractmethod
    async def success_publish(self, message: dict[str, Any], vehicle_id: int | None = None) -> None:
        """Опубликовать сообщение о подтверждении доставки."""
        raise NotImplementedError
