"""Абстракция обработчика агрегата FanOutPayload."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class FanOutPayload(Protocol):
    """
    Structural type for the FanOutPayload received from cdc-distributor.

    Any object with these attributes satisfies this Protocol.
    """

    seq_id: int
    low_offset: int
    up_offset: int
    tables: dict[str, Any]  # table_name -> TableBatch


@runtime_checkable
class AggregateHandler(Protocol):
    """
    Интерфейс обработчика агрегата.

    handle_raw: принимает сырые байты, декодирует и применяет.
                Используется AmqpConsumer как точка входа для сообщения.
    handle:     принимает уже декодированный FanOutPayload.
                Предназначен для подклассов (ProcessAndNotification и т.д.)

    Example:
        class MyHandler:
            async def handle_raw(self, body: bytes) -> None:
                payload = decode(body)
                await self.handle(payload)

            async def handle(self, payload: FanOutPayload) -> None:
                ...
    """

    async def handle_raw(self, body: bytes) -> None:
        """Обработать сырые байты AMQP сообщения."""
        ...

    async def handle(self, payload: FanOutPayload) -> None:
        """
        Обрабатывает один FanOutPayload агрегат.

        Args:
            payload: FanOutPayload агрегат от cdc-distributor.
                Содержит seq_id, low_offset, up_offset, tables.
        """
        ...
