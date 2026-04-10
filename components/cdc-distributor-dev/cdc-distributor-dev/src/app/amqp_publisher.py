"""AMQP-паблишер для публикации агрегатов в очереди бортов."""

import asyncio
import random

from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractChannel
from aio_pika.pool import Pool
from loguru import logger

from src.core.amqp.queue_name import queue_name


class AMQPPublisher:
    """Публикует сообщение в очередь конкретного борта с retry.

    Использует канал из пула (channel_pool) с publisher confirms.
    При ошибке публикации выполняет retry с exponential backoff.
    После исчерпания retry выбрасывает исключение.
    """

    def __init__(
        self,
        channel_pool: Pool[AbstractChannel],
        *,
        max_retries: int = 3,
        initial_delay: float = 0.5,
        max_delay: float = 10.0,
        backoff_base: float = 2.0,
        jitter: bool = True,
    ) -> None:
        self._channel_pool = channel_pool
        self._max_retries = max_retries
        self._initial_delay = initial_delay
        self._max_delay = max_delay
        self._backoff_base = backoff_base
        self._jitter = jitter

    async def publish(
        self,
        bort_id: int,
        service_name: str,
        body: bytes,
    ) -> None:
        """Публикует сообщение в очередь борта с retry.

        Args:
            bort_id: идентификатор борта
            service_name: имя сервиса (graph, enterprise, auth, trip)
            body: сериализованный payload (bytes от msgspec.json.encode)

        Raises:
            Exception: если все retry исчерпаны
        """
        target_queue = queue_name(bort_id, service_name)
        message = Message(
            body=body,
            delivery_mode=DeliveryMode.PERSISTENT,  # SER-03: delivery_mode=2
        )

        delay = self._initial_delay
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                async with self._channel_pool.acquire() as channel:
                    # Публикуем напрямую в default exchange с routing_key = queue name
                    await channel.default_exchange.publish(
                        message,
                        routing_key=target_queue,
                    )
                # Publisher confirm succeeded — broker ack'd
                logger.debug(
                    "Published to queue={queue} bort={bort} service={service} attempt={attempt}",
                    queue=target_queue,
                    bort=bort_id,
                    service=service_name,
                    attempt=attempt,
                )
                return
            except Exception as e:
                last_error = e
                if attempt < self._max_retries:
                    sleep_time = min(delay, self._max_delay)
                    if self._jitter:
                        jitter_amount = sleep_time * 0.1
                        sleep_time += random.uniform(-jitter_amount, jitter_amount)  # noqa: S311
                    logger.warning(
                        "Publish failed queue={queue} bort={bort} "
                        "attempt={attempt}/{max} error={error}, "
                        "retrying in {delay:.2f}s",
                        queue=target_queue,
                        bort=bort_id,
                        attempt=attempt,
                        max=self._max_retries,
                        error=str(e),
                        delay=sleep_time,
                    )
                    await asyncio.sleep(sleep_time)
                    delay *= self._backoff_base

        # All retries exhausted
        logger.error(
            "Publish failed after all retries queue={queue} "
            "bort={bort} retries={retries} error={error}",
            queue=target_queue,
            bort=bort_id,
            retries=self._max_retries,
            error=str(last_error),
        )
        raise last_error  # type: ignore[misc]
