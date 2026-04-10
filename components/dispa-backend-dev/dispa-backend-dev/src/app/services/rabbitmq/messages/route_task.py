"""Обработчик сообщений типа `route_task`."""

from typing import Any

from app.api.schemas import RouteTaskUpdate
from app.enums import TripStatusRouteEnum
from app.enums.config import ServiceModeEnum
from app.services.rabbitmq.config.enum import MessageTypeEnum
from app.services.rabbitmq.config.logger import get_logger
from app.services.rabbitmq.main import publisher_manager
from app.services.rabbitmq.schemas import BaseMsgScheme
from app.services.tasks.route_task import RouteTaskService

from .base import BaseMessageHandler

logger = get_logger()


class RouteTaskMessageHandler(BaseMessageHandler):
    """Обработчик сообщений о сменных заданиях."""

    type_message = MessageTypeEnum.route_task

    async def handle_insert(self, message: dict[str, Any]) -> bool:
        """Обработка события создания."""
        response = False
        if self.mode == ServiceModeEnum.bort and message["payload"]["status"] == TripStatusRouteEnum.SENT:
            message["payload"]["status"] = TripStatusRouteEnum.DELIVERED
            update_model = RouteTaskUpdate.model_validate(message["payload"])
            try:
                async with self.session_scope() as session:
                    await RouteTaskService(session).update(message["payload"]["id"], update_model)
                    await publisher_manager.task_publish(BaseMsgScheme.model_validate(message))
                    response = False
            except Exception as e:
                logger.exception("Ошибка обновления статуса задания на смену", exc_info=e)
                raise
        elif self.mode == ServiceModeEnum.server and message["payload"]["status"] == TripStatusRouteEnum.DELIVERED:
            update_model = RouteTaskUpdate.model_validate(message["payload"])
            try:
                async with self.session_scope() as session:
                    await RouteTaskService(session).update(message["payload"]["id"], update_model)
                    response = True
            except Exception as e:
                logger.exception("Ошибка обновления статуса задания на смену", exc_info=e)
                raise
        else:
            logger.info(
                "Событие create для route_task не поддерживается",
                event_message=message["message_data"]["message_event"],
            )
        return response

    async def handle_update(self, message: dict[str, Any]) -> bool:
        """Обработка события обновления."""
        logger.info(
            "Событие update для route_task не поддерживается",
            event_message=message["message_data"]["message_event"],
        )
        return False

    async def handle_delete(self, message: dict[str, Any]) -> bool:
        """Обработка события удаления."""
        logger.info(
            "Событие delete для route_task не поддерживается",
            event_message=message["message_data"]["message_event"],
        )
        return False

    async def handle_cancel(self, message: dict[str, Any]) -> bool:
        """Обработка события отмены."""
        logger.info(
            "Событие cancel для route_task не поддерживается",
            event_message=message["message_data"]["message_event"],
        )
        return False

    async def handle_activate(self, message: dict[str, Any]) -> bool:
        """Обработка события активации."""
        logger.info(
            "Событие activate для route_task не поддерживается",
            event_message=message["message_data"]["message_event"],
        )
        return False
