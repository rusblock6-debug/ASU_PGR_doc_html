"""Обработчик сообщений типа `shift_task`."""

from typing import Any

from app.services.rabbitmq.config.enum import MessageTypeEnum
from app.services.rabbitmq.config.logger import get_logger

from .base import BaseMessageHandler

logger = get_logger()


class ShiftTaskMessageHandler(BaseMessageHandler):
    """Обработчик сообщений о сменных заданиях."""

    type_message = MessageTypeEnum.shift_task

    async def handle_insert(self, message: dict[str, Any]) -> bool:
        """Обработка события создания."""
        logger.info(
            "Событие create для shift_task не поддерживается",
            event_message=message["message_data"]["message_event"],
        )
        return False

    async def handle_update(self, message: dict[str, Any]) -> bool:
        """Обработка события обновления."""
        logger.info(
            "Событие update для shift_task не поддерживается",
            event_message=message["message_data"]["message_event"],
        )
        return False

    async def handle_delete(self, message: dict[str, Any]) -> bool:
        """Обработка события удаления."""
        logger.info(
            "Событие delete для shift_task не поддерживается",
            event_message=message["message_data"]["message_event"],
        )
        return False

    async def handle_cancel(self, message: dict[str, Any]) -> bool:
        """Обработка события отмены."""
        logger.info(
            "Событие cancel для shift_task не поддерживается",
            event_message=message["message_data"]["message_event"],
        )
        return False

    async def handle_activate(self, message: dict[str, Any]) -> bool:
        """Обработка события активации."""
        logger.info(
            "Событие activate для shift_task не поддерживается",
            event_message=message["message_data"]["message_event"],
        )
        return False
