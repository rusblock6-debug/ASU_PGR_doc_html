"""Роутер для регистрации обработчиков стримов."""

from collections.abc import Awaitable, Callable
from typing import Any

import msgspec
import msgspec.json


class BatchMetadata(msgspec.Struct):
    """Метаданные batch для offset tracking."""

    stream_name: str
    max_offset: int  # Максимальный offset в batch
    min_offset: int  # Минимальный offset в batch


class StreamHandlerConfig(msgspec.Struct):
    """Конфигурация обработчика стрима."""

    name: str
    batch_size: int
    timeout: float
    handler: Callable[[Any, BatchMetadata], Awaitable[None]]
    decoder: msgspec.json.Decoder[Any]


class StreamRouter:
    """Роутер для маршрутизации стримов к обработчикам."""

    def __init__(self) -> None:
        self._handlers: dict[str, StreamHandlerConfig] = {}

    def subscribe[T](
        self,
        name: str,
        *,
        event_type: type[T],
        batch_size: int = 100,
        timeout: float = 1.0,
    ) -> Callable[
        [Callable[..., Awaitable[None]]],
        Callable[..., Awaitable[None]],
    ]:
        """Регистрирует async-обработчик стрима.

        Args:
            name: имя стрима
            event_type: тип события для декодирования
            batch_size: размер батча
            timeout: таймаут для flush
        """
        decoder = msgspec.json.Decoder(event_type)

        def decorator(
            func: Callable[..., Awaitable[None]],
        ) -> Callable[..., Awaitable[None]]:
            if not callable(func):
                raise TypeError("Handler must be callable")

            if name in self._handlers:
                raise ValueError(f"Stream '{name}' already registered")

            self._handlers[name] = StreamHandlerConfig(
                name=name,
                batch_size=batch_size,
                timeout=timeout,
                handler=func,
                decoder=decoder,
            )

            return func

        return decorator

    def get(self, name: str) -> StreamHandlerConfig:
        """Получить конфигурацию обработчика по имени стрима."""
        try:
            return self._handlers[name]
        except KeyError:
            raise KeyError(f"Stream '{name}' is not registered") from None

    def all(self) -> list[StreamHandlerConfig]:
        """Получить все зарегистрированные конфигурации обработчиков."""
        return list(self._handlers.values())
