"""Обработчик сообщений типа `dispatcher_assignments`."""

from typing import Any

from app.core.redis_client import redis_client
from app.enums.config import ServiceModeEnum
from app.services.rabbitmq.config.enum import MessageTypeEnum
from app.services.rabbitmq.config.logger import get_logger
from app.services.route_summary import decide_dispatcher_assignment

from .base import BaseMessageHandler

logger = get_logger()


class DispatcherAssignmentsMessageHandler(BaseMessageHandler):
    """Обработчик сообщений о сменных заданиях."""

    type_message = MessageTypeEnum.dispatcher_assignments

    async def handle_insert(self, message: dict[str, Any]) -> bool:
        """Обработка события создания."""
        response = False
        if self.mode == ServiceModeEnum.bort and message.get("assignment_id", None) is None:
            message["event_type"] = "assignments_alert"
            channel = f"trip-service:vehicle:{message['payload']['vehicle_id']}:alert"
            published = await redis_client.publish(channel, message)
            if not published:
                raise RuntimeError("failed to publish dispatcher_assignments to Redis")

            logger.info(
                "Получено изменение статуса НЗ",
                message_id=message["payload"].get("id", None),
                channel=channel,
                target_vehicle_id=message["payload"].get("vehicle_id", None),
            )
            response = True
        else:
            logger.info(
                "Событие create для dispatcher_assignments не поддерживается",
                event_message=message["message_data"]["message_event"],
                mode=self.mode,
            )
        return response

    async def handle_update(self, message: dict[str, Any]) -> bool:
        """Обработка события обновления."""
        response = False
        if self.mode == ServiceModeEnum.server and message["payload"].get("assignment_id", None) is not None:
            try:
                async with self.session_scope() as session:
                    await decide_dispatcher_assignment(
                        assignment_id=message["payload"]["assignment_id"],
                        approved=message["payload"]["approved"],
                        db=session,
                    )
                logger.success(
                    "Наряд задание успешно обновлено",
                    assignment_id=message["payload"]["assignment_id"],
                    approved=message["payload"]["approved"],
                )
            except Exception as exc:
                logger.error("Ошибка обновления наряд задания", exc=exc)
        else:
            logger.info(
                "Событие update для dispatcher_assignments не поддерживается",
                event_message=message["message_data"]["message_event"],
                mode=self.mode,
            )
        return response

    async def handle_delete(self, message: dict[str, Any]) -> bool:
        """Обработка события удаления."""
        logger.info(
            "Событие delete для dispatcher_assignments не поддерживается",
            event_message=message["message_data"]["message_event"],
        )
        return False

    async def handle_cancel(self, message: dict[str, Any]) -> bool:
        """Обработка события отмены."""
        logger.info(
            "Событие cancel для dispatcher_assignments не поддерживается",
            event_message=message["message_data"]["message_event"],
        )
        return False

    async def handle_activate(self, message: dict[str, Any]) -> bool:
        """Обработка события активации."""
        logger.info(
            "Событие activate для dispatcher_assignments не поддерживается",
            event_message=message["message_data"]["message_event"],
        )
        return False
