"""Перечисления для сообщений RabbitMQ."""

from enum import StrEnum


class MessageEventEnum(StrEnum):
    """Типы событий сообщений."""

    create = "create"
    update = "update"
    delete = "delete"
    cancel = "cancel"
    activate = "activate"


class MessageTypeEnum(StrEnum):
    """Типы сообщений."""

    shift_task = "shift_tasks"
    route_task = "route_tasks"
    dispatcher_assignments = "dispatcher_assignments"
