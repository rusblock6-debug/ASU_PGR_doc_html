"""Entry point для CDC Bort Applier."""

import asyncio
import logging
import signal

from loguru import logger

from src.app.bootstrap import create_consumers
from src.app.outbox_worker import OutboxWorker
from src.core.config import settings
from src.core.logging import LogConfig, LogFormat, setup_logging


async def main() -> None:
    setup_logging(LogConfig(level=logging.INFO, format=LogFormat.TEXT, colorize=True))
    logger.info(
        "CDC Bort Applier starting bort_id={bort_id}",
        bort_id=settings.VEHICLE_ID,
    )

    shutdown = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown.set)

    result = await create_consumers()

    if not result.consumers:
        logger.error("No services configured — check POSTGRES_URL env vars. Exiting.")
        return

    outbox_worker: OutboxWorker | None = None
    if result.outbox_pool is not None:
        outbox_worker = OutboxWorker(
            pool=result.outbox_pool,
            amqp_url=settings.AMQP_URL,
        )
        await outbox_worker.start()

    try:
        tasks: list[asyncio.Task[None]] = []
        for consumer in result.consumers:
            tasks.append(asyncio.ensure_future(consumer.start()))
        await asyncio.gather(*tasks)
        logger.info(
            "All consumers started count={count} bort_id={bort_id}",
            count=len(result.consumers),
            bort_id=settings.VEHICLE_ID,
        )

        worker_task: asyncio.Task[None] | None = None
        if outbox_worker is not None:
            worker_task = asyncio.create_task(outbox_worker.run())

        await shutdown.wait()
    finally:
        if outbox_worker is not None:
            await outbox_worker.stop()
        if worker_task is not None:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
        logger.info(
            "Shutting down {count} consumer(s)...",
            count=len(result.consumers),
        )
        for consumer in result.consumers:
            await consumer.stop()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
