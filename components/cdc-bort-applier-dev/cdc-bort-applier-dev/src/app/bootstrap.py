"""Bootstrap: create consumers for all enabled services."""

from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Any

import asyncpg
from loguru import logger

from src.api.streams import ServiceConsumerConfig, create_service_consumer
from src.app.factories.auth import AuthFactory
from src.app.factories.enterpise import EnterpriseFactory
from src.app.factories.graph import GraphFactory
from src.app.factories.trip import TripFactory
from src.app.outbox import OutboxRule, CdcOp
from src.core.amqp.consumer import AmqpConsumer
from src.core.config import settings

_TRIP_QUEUE_NAME = f"server.bort_{settings.VEHICLE_ID}.trip.dst"

_TRIP_OUTBOX_RULES = (
    OutboxRule(
        table="dispatcher_assignments",
        queue_name=_TRIP_QUEUE_NAME,
        ops=frozenset((CdcOp.CREATE,)),
    ),
    OutboxRule(
        table="route_tasks",
        queue_name=_TRIP_QUEUE_NAME,
        ops=frozenset((CdcOp.CREATE,)),
    ),
)

SERVICE_CONFIGS = (
    ServiceConsumerConfig("graph", GraphFactory, settings.graph_service),
    ServiceConsumerConfig("enterprise", EnterpriseFactory, settings.enterprise_service),
    ServiceConsumerConfig("auth", AuthFactory, settings.auth_service),
    ServiceConsumerConfig(
        "trip",
        TripFactory,
        settings.trip_service,
        outbox_rules=_TRIP_OUTBOX_RULES,
    ),
)


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    """Result of bootstrap: consumers + optional outbox pool."""

    consumers: list[AmqpConsumer]
    outbox_pool: asyncpg.Pool[Any] | None


async def create_consumers() -> BootstrapResult:
    """Create AmqpConsumer instances for all services with configured POSTGRES_HOST.

    Services where POSTGRES_HOST is None are skipped with a log message.
    All enabled services are initialized concurrently.
    Returns BootstrapResult with consumers and an outbox pool (if any service has outbox rules).
    """
    tasks = []
    names: list[str] = []

    for cfg in SERVICE_CONFIGS:
        if cfg.db_settings.POSTGRES_URL is not None:
            tasks.append(asyncio.ensure_future(create_service_consumer(cfg)))
            names.append(cfg.service_name)
        else:
            logger.info(
                "{service} service skipped — POSTGRES_URL not configured",
                service=cfg.service_name.capitalize(),
            )

    results = await asyncio.gather(*tasks)

    consumers: list[AmqpConsumer] = []
    outbox_pool: asyncpg.Pool[Any] | None = None

    for result in results:
        consumers.append(result.consumer)
        if result.has_outbox and outbox_pool is None:
            outbox_pool = result.pool

    for name in names:
        logger.info(
            "{service} service consumer created",
            service=name.capitalize(),
        )

    return BootstrapResult(consumers=consumers, outbox_pool=outbox_pool)
