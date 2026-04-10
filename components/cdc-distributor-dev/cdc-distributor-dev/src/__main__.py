"""CDC Distributor — fan-out relay для публикации CDC-стримов в очереди бортов."""

import asyncio
import logging
import signal

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from loguru import logger

from src.api.streams import auth_service, enterprise_service, graph_service, trip_service
from src.app.amqp_publisher import AMQPPublisher
from src.app.bort_offset_manager import BortOffsetManager
from src.app.factories.auth import AuthFactory
from src.app.factories.enterpise import EnterpriseFactory
from src.app.factories.graph import GraphFactory
from src.app.factories.trip import TripFactory
from src.core.amqp.connection_manager import AMQPConnectionManager
from src.core.amqp.queue_name import queue_name
from src.core.config import settings
from src.core.db.session import async_engine, async_session_factory
from src.core.logging import LogConfig, LogFormat, setup_logging
from src.core.rstream import RetryConfig, StreamAppConfig, StreamAppManager
from src.core.rstream.app import BortOffsetAdapter, make_bort_lifespan
from src.core.rstream.router import StreamRouter

# Service registry: service_name -> (router, factory_class)
SERVICE_ROUTERS: dict[str, tuple[StreamRouter, type]] = {
    "graph": (graph_service.router, GraphFactory),
    "enterprise": (enterprise_service.router, EnterpriseFactory),
    "auth": (auth_service.router, AuthFactory),
    "trip": (trip_service.router, TripFactory),
}


async def main() -> None:
    """Точка входа CDC Distributor."""
    log_config = LogConfig(
        level=logging.INFO,
        format=LogFormat.TEXT,
        colorize=True,
    )
    setup_logging(log_config)
    logger.info("Starting CDC Distributor")

    amqp_manager = AMQPConnectionManager(
        host=settings.RABBIT_AMQP_HOST,
        port=settings.RABBIT_AMQP_PORT,
        login=settings.RABBIT_AMQP_USER,
        password=settings.RABBIT_AMQP_PASSWORD,
        channel_pool_size=max(len(settings.BORT_IDS) * 2, 10),
    )

    # 2. Create shared BortOffsetManager
    offset_manager = BortOffsetManager(async_session_factory)

    # 4. Start AMQP connection
    await amqp_manager.start()

    # 5. Declare durable queues for all (bort x service) at startup
    async with amqp_manager.channel_pool.acquire() as channel:
        for service_name in SERVICE_ROUTERS:
            for bort_id in settings.BORT_IDS:
                q_name = queue_name(bort_id, service_name)
                await channel.declare_queue(q_name, durable=True)
                logger.info("Declared durable queue={queue}", queue=q_name)

    # 6. Create shared AMQPPublisher
    publisher = AMQPPublisher(amqp_manager.channel_pool)

    # 7. Generate StreamAppConfig for each (service x bort)
    #    Total configs = len(BORT_IDS) * len(SERVICE_ROUTERS) = 4*N
    app_configs: list[StreamAppConfig] = []

    for service_name, (service_router, factory_cls) in SERVICE_ROUTERS.items():
        for bort_id in settings.BORT_IDS:
            # Separate consumer per (bort x service)
            factory = factory_cls(
                publisher=publisher,
                offset_manager=offset_manager,
                bort_id=bort_id,
                service_name=service_name,
            )

            # Per-bort offset adapter for StreamApp initial offset loading
            offset_adapter = BortOffsetAdapter(offset_manager, bort_id)

            app_name = f"{service_name}:bort_{bort_id}"
            lifespan = make_bort_lifespan(
                factory=factory,
                offset_adapter=offset_adapter,
            )

            app_configs.append(
                StreamAppConfig(
                    name=app_name,
                    router=service_router,
                    host=settings.RABBIT_HOST,
                    port=settings.RABBIT_PORT,
                    vhost=settings.RABBIT_VHOST,
                    username=settings.RABBIT_USER,
                    password=settings.RABBIT_PASSWORD,
                    lifespan=lifespan,
                ),
            )

    logger.info(
        "Generated {count} StreamApp configs for {borts} borts x {services} services",
        count=len(app_configs),
        borts=len(settings.BORT_IDS),
        services=len(SERVICE_ROUTERS),
    )

    # Configure retry behavior
    retry_config = RetryConfig(
        max_retries=settings.retry.MAX_RETRIES,
        initial_delay=settings.retry.INITIAL_DELAY,
        max_delay=settings.retry.MAX_DELAY,
        exponential_base=settings.retry.EXPONENTIAL_BASE,
        jitter=settings.retry.JITTER,
    )

    manager = StreamAppManager(app_configs, retry_config=retry_config)

    # Signal handling for graceful shutdown
    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def signal_handler() -> None:
        logger.info("Received shutdown signal")
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await manager.start()

        run_task = asyncio.create_task(manager.run())
        shutdown_task = asyncio.create_task(shutdown_event.wait())

        done, pending = await asyncio.wait(
            [run_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    finally:
        await manager.stop()
        await amqp_manager.stop()
        await async_engine.dispose()
        logger.info("Application stopped")


def _run_migrations() -> None:
    """Запуск Alembic миграций перед стартом приложения."""
    logger.info("Running database migrations")
    alembic_cfg = AlembicConfig("alembic.ini")
    alembic_command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations completed")


if __name__ == "__main__":
    _run_migrations()
    asyncio.run(main())
