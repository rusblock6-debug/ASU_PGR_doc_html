"""Background worker that publishes unsent outbox messages to RabbitMQ."""

from __future__ import annotations
import asyncio
from typing import Any

import aio_pika
import aio_pika.abc
import asyncpg
from loguru import logger


_SELECT_UNSENT = """
SELECT id, queue_name, payload::text
FROM outbox
WHERE sent_at IS NULL
ORDER BY created_at
LIMIT $1
"""

_MARK_SENT = """
UPDATE outbox
SET sent_at = now()
WHERE id = $1
"""


class OutboxWorker:
    """Periodically reads unsent outbox records and publishes them to RabbitMQ.

    Uses an existing asyncpg.Pool for DB access and creates its own
    aio-pika RobustConnection for publishing.
    """

    POLL_INTERVAL: float = 5.0
    BATCH_SIZE: int = 100

    def __init__(
        self,
        pool: asyncpg.Pool[Any],
        amqp_url: str,
        poll_interval: float = POLL_INTERVAL,
        batch_size: int = BATCH_SIZE,
    ) -> None:
        self._pool = pool
        self._amqp_url = amqp_url
        self._poll_interval = poll_interval
        self._batch_size = batch_size
        self._running = False
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None

    async def start(self) -> None:
        """Connect to RabbitMQ and start the polling loop."""
        self._connection = await aio_pika.connect_robust(self._amqp_url)
        self._channel = await self._connection.channel(publisher_confirms=True)
        await self._channel.set_qos(prefetch_count=1)
        self._running = True
        logger.info(
            "OutboxWorker started poll_interval={interval}s batch_size={batch}",
            interval=self._poll_interval,
            batch=self._batch_size,
        )

    async def stop(self) -> None:
        """Stop the polling loop and close the RabbitMQ connection."""
        self._running = False
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()
        logger.info("OutboxWorker stopped")

    async def run(self) -> None:
        """Run the polling loop until stopped."""
        while self._running:
            try:
                sent = await self._poll_and_publish()
                if sent > 0:
                    logger.info(
                        "OutboxWorker published {count} message(s)",
                        count=sent,
                    )
            except Exception:
                logger.exception("OutboxWorker poll cycle failed")
            await asyncio.sleep(self._poll_interval)

    async def _poll_and_publish(self) -> int:
        """Select unsent records and publish them. Returns number of messages sent."""
        assert self._channel is not None

        rows: list[asyncpg.Record] = await self._pool.fetch(
            _SELECT_UNSENT,
            self._batch_size,
        )
        logger.debug("OutboxWorker polled rows={count}", count=len(rows))
        if not rows:
            return 0

        sent = 0
        for row in rows:
            row_id: int = row["id"]
            queue_name: str = row["queue_name"]
            payload: str = row["payload"]

            logger.debug(
                "OutboxWorker processing id={id} queue={queue} payload={payload}",
                id=row_id,
                queue=queue_name,
                payload=payload,
            )

            try:
                confirmation = await self._channel.default_exchange.publish(
                    aio_pika.Message(
                        body=payload.encode("utf-8"),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    ),
                    routing_key=queue_name,
                    mandatory=True,
                    timeout=5.0,
                )
                if not confirmation:
                    logger.warning(
                        "OutboxWorker publish NACK id={id} queue={queue}",
                        id=row_id,
                        queue=queue_name,
                    )
                    continue
                logger.debug(
                    "OutboxWorker broker confirmation={confirmation} id={id}",
                    confirmation=confirmation,
                    id=row_id,
                )
                await self._pool.execute(_MARK_SENT, row_id)
                sent += 1
                logger.debug(
                    "OutboxWorker marked sent id={id} queue={queue}",
                    id=row_id,
                    queue=queue_name,
                )
            except Exception:
                logger.exception(
                    "OutboxWorker failed to send id={id} queue={queue}",
                    id=row_id,
                    queue=queue_name,
                )
        return sent
