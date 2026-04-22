"""AMQP consumer wrapper с RobustConnection и ACK-after-commit семантикой."""

from typing import Any

import aio_pika
import aio_pika.abc
import asyncpg
from loguru import logger

from src.core.config import settings

# Ошибки БД, при которых retry бессмысленен — данные не изменятся
_PERMANENT_DB_ERRORS = (
    asyncpg.UniqueViolationError,
    asyncpg.ForeignKeyViolationError,
    asyncpg.NotNullViolationError,
    asyncpg.CheckViolationError,
    asyncpg.ExclusionViolationError,
    asyncpg.DataError,
)

_DEFAULT_MAX_RETRIES = 3


class AmqpConsumer:
    """
    AMQP consumer для одного сервиса (graph / enterprise / auth / trip).

    Создаёт RobustConnection, объявляет очередь passive, регистрирует callback.
    ACK отправляется только после успешного выполнения handler.handle_raw().
    Permanent DB errors (constraint violations) — nack(requeue=False) сразу.
    Transient errors — nack(requeue=True) до max_retries, затем nack(requeue=False).
    """

    def __init__(
        self,
        service_name: str,
        queue_name: str,
        handler: Any,
        prefetch_count: int = 10,
        max_retries: int = _DEFAULT_MAX_RETRIES,
    ) -> None:
        """
        Args:
            service_name: Имя сервиса ("graph", "enterprise", "auth", "trip")
            queue_name: Полное имя очереди, e.g. "server.bort_4.cdc_graph.dst"
            handler: Обработчик агрегата, реализующий AggregateHandler Protocol
            prefetch_count: Количество непроцессированных сообщений
            max_retries: Максимальное число retry для transient ошибок
        """
        self._service_name = service_name
        self._queue_name = queue_name
        self._handler = handler
        self._prefetch_count = prefetch_count
        self._max_retries = max_retries
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None

    async def start(self) -> None:
        """Подключиться к AMQP и начать потребление."""
        self._connection = await aio_pika.connect_robust(settings.AMQP_URL)
        self._connection.reconnect_callbacks.add(self._on_reconnect)
        channel = await self._connection.channel()
        await channel.set_qos(prefetch_count=self._prefetch_count)
        queue = await channel.declare_queue(self._queue_name, durable=True)
        logger.info(
            "Consumer started service={service} queue={queue} bort_id={bort_id}",
            service=self._service_name,
            queue=self._queue_name,
            bort_id=settings.VEHICLE_ID,
        )
        await queue.consume(self._on_message, no_ack=False)

    async def stop(self) -> None:
        """Закрыть соединение."""
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()
            logger.info(
                "Consumer stopped service={service}",
                service=self._service_name,
            )

    async def _on_message(
        self,
        message: aio_pika.abc.AbstractIncomingMessage,
    ) -> None:
        """Callback для входящих сообщений. ACK только после успешного handle_raw."""
        try:
            await self._handler.handle_raw(message.body)
        except _PERMANENT_DB_ERRORS as exc:
            logger.error(
                "Permanent DB error — dropping message"
                " service={service} queue={queue} error={error}"
                " body={body}",
                service=self._service_name,
                queue=self._queue_name,
                error=str(exc),
                body=message.body.decode(errors="replace"),
            )
            await message.nack(requeue=False)
            return
        except Exception:
            delivery_count = self._get_delivery_count(message)
            if delivery_count >= self._max_retries:
                logger.error(
                    "Max retries exceeded — dropping message"
                    " service={service} queue={queue} retries={retries}"
                    " body={body}",
                    service=self._service_name,
                    queue=self._queue_name,
                    retries=delivery_count,
                    body=message.body.decode(errors="replace"),
                )
                await message.nack(requeue=False)
            else:
                logger.exception(
                    "Apply failed service={service} queue={queue} retry={retry}/{max}",
                    service=self._service_name,
                    queue=self._queue_name,
                    retry=delivery_count,
                    max=self._max_retries,
                )
                await message.nack(requeue=True)
            return
        await message.ack()

    @staticmethod
    def _get_delivery_count(message: aio_pika.abc.AbstractIncomingMessage) -> int:
        """Получить количество доставок из headers (quorum queue) или x-death (classic)."""
        headers = message.headers or {}
        # Quorum queues: x-delivery-count header
        count = headers.get("x-delivery-count")
        if isinstance(count, int):
            return count
        # Classic queues: x-death header с count
        x_death = headers.get("x-death")
        if isinstance(x_death, list) and x_death:
            first = x_death[0]
            if isinstance(first, dict):
                death_count = first.get("count", 0)
                if isinstance(death_count, int):
                    return death_count
        return 0

    def _on_reconnect(self, connection: object) -> None:
        """Callback при reconnect."""
        logger.info(
            "Reconnected to AMQP service={service}",
            service=self._service_name,
        )
