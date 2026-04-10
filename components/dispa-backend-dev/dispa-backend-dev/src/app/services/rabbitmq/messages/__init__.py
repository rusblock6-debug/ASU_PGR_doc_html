"""Обработчики и роутер сообщений RabbitMQ."""

from .assignment import DispatcherAssignmentsMessageHandler
from .base import BaseMessageHandler, MessageHandlerRouter
from .route_task import RouteTaskMessageHandler
from .shift_task import ShiftTaskMessageHandler

type_message_handlers: list[type[BaseMessageHandler]] = [
    DispatcherAssignmentsMessageHandler,
    ShiftTaskMessageHandler,
    RouteTaskMessageHandler,
]

__all__ = [
    "BaseMessageHandler",
    "MessageHandlerRouter",
    "DispatcherAssignmentsMessageHandler",
    "ShiftTaskMessageHandler",
    "RouteTaskMessageHandler",
    "type_message_handlers",
]
