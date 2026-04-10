"""Базовая схема сообщений RabbitMQ."""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.services.rabbitmq.config.enum import MessageEventEnum, MessageTypeEnum


class MessageData(BaseModel):
    """Базовый набор полей сообщения."""

    message_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    message_event: MessageEventEnum = MessageEventEnum.create
    message_type: MessageTypeEnum = MessageTypeEnum.route_task
    message_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BaseTransportModel(BaseModel):
    """Базовая схема моделей транспорта RabbitMQ."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class BaseMsgScheme(BaseTransportModel):
    """Базовая схема сообщения."""

    payload: dict[str, Any]
    message_data: MessageData = Field(default_factory=MessageData)
