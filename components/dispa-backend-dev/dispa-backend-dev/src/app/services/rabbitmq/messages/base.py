"""Базовые классы и роутер обработчиков сообщений RabbitMQ."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from typing import Any, ClassVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.session import AsyncSessionLocal
from app.enums.config import ServiceModeEnum
from app.services.rabbitmq.config.enum import MessageEventEnum, MessageTypeEnum
from app.services.rabbitmq.config.logger import get_logger
from app.services.rabbitmq.exception import MessageHandlerError, MessageHandlerNotFoundError, UnknownMessageTypeError

logger = get_logger()


class BaseMessageHandler(ABC):
    """Базовый класс обработчик сообщения."""

    type_message: ClassVar[MessageTypeEnum]

    @property
    def mode(self) -> ServiceModeEnum:
        """Режим работы сервиса."""
        return settings.service_mode

    @property
    def vehicle_id(self) -> int:
        """Режим работы сервиса."""
        return int(settings.vehicle_id)

    @asynccontextmanager
    async def session_scope(self) -> AsyncIterator[AsyncSession]:
        """Предоставляет транзакционную async-сессию для операций хендлера."""
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @abstractmethod
    async def handle_insert(self, message: dict[str, Any]) -> bool:
        """Обработка сообщения по событию создания."""
        raise NotImplementedError()

    @abstractmethod
    async def handle_update(self, message: dict[str, Any]) -> bool:
        """Обработка сообщения по событию обновления."""
        raise NotImplementedError()

    @abstractmethod
    async def handle_delete(self, message: dict[str, Any]) -> bool:
        """Обработка сообщения по событию удаления."""
        raise NotImplementedError()

    @abstractmethod
    async def handle_cancel(self, message: dict[str, Any]) -> bool:
        """Обработка сообщения по событию закрытия."""
        raise NotImplementedError()

    @abstractmethod
    async def handle_activate(self, message: dict[str, Any]) -> bool:
        """Обработка сообщения по событию активации."""
        raise NotImplementedError()

    async def handle(self, data: dict[str, Any]) -> bool:
        """Базовый пайплайн обработки сообщения."""
        response = True
        event_message = data["message_data"]["message_event"]
        match event_message:
            case MessageEventEnum.create:
                response = await self.handle_insert(data)
            case MessageEventEnum.update:
                response = await self.handle_update(data)
            case MessageEventEnum.delete:
                response = await self.handle_delete(data)
            case MessageEventEnum.cancel:
                response = await self.handle_cancel(data)
            case MessageEventEnum.activate:
                response = await self.handle_activate(data)
            case _:
                logger.error("Обработчик события отсутствует.", event_message=event_message)
        return response


class MessageHandlerRouter:
    """Роутер, выбирающий обработчик по `type_message`."""

    def __init__(self, handlers: Iterable[type[BaseMessageHandler]] | None = None) -> None:
        self._handlers: dict[MessageTypeEnum, BaseMessageHandler] = {}
        if handlers:
            for handler in handlers:
                self.register(handler)

    def register(self, handler_cls: type[BaseMessageHandler]) -> None:
        """Регистрирует обработчик для его `type_message`."""
        msg_type = getattr(handler_cls, "type_message", None)
        if not isinstance(msg_type, MessageTypeEnum):
            raise MessageHandlerError(
                f"Класс {handler_cls.__name__} должен определить `type_message: MessageTypeEnum`.",
            )
        self._handlers[msg_type] = handler_cls()

    def get_handler(self, message: dict[str, Any]) -> BaseMessageHandler:
        """Возвращает обработчик, подходящий для входящего сообщения."""
        if "message_type" not in message["message_data"]:
            raise UnknownMessageTypeError("В сообщении отсутствует поле `message_type`.")
        try:
            msg_type = MessageTypeEnum(message["message_data"]["message_type"])
        except ValueError as exc:
            raise UnknownMessageTypeError(
                f"Неизвестный `message_type`: {message['message_data']['message_type']}",
            ) from exc

        handler = self._handlers.get(msg_type)
        if handler is None:
            raise MessageHandlerNotFoundError(f"Для `message_type={msg_type}` не зарегистрирован обработчик.")
        return handler

    async def dispatch(self, message: dict[str, Any]) -> bool:
        """Маршрутизирует сообщение в подходящий обработчик."""
        logger.info("Полученное сообщение: ", message=message)
        handler = self.get_handler(message)
        return await handler.handle(message)
