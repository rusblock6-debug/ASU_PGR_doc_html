"""Generic consumer factory replacing per-service stream files."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

import asyncpg

from src.app.aggregate_applier import AggregateApplier
from src.app.factories.service_factory import ServiceFactory
from src.app.outbox import OutboxRule, OutboxWriter
from src.core.amqp.consumer import AmqpConsumer
from src.core.config import DatabaseServiceSettings, settings
from src.core.registry import ServiceRegistry


@dataclass(frozen=True, slots=True)
class ServiceConsumerConfig:
    """Declarative config for a single service consumer."""

    service_name: str
    factory_class: type[ServiceFactory]
    db_settings: DatabaseServiceSettings
    outbox_rules: tuple[OutboxRule, ...] = ()


@dataclass(frozen=True, slots=True)
class ServiceConsumerResult:
    """Result of creating a service consumer — includes pool for sharing."""

    consumer: AmqpConsumer
    pool: asyncpg.Pool[Any]
    has_outbox: bool


async def create_service_consumer(
    config: ServiceConsumerConfig,
) -> ServiceConsumerResult:
    """Create an AmqpConsumer for any service from a declarative config.

    Creates DB pool, ServiceRegistry, factory, AggregateApplier.
    Calls applier.setup() to ensure cdc_seq_id table exists.
    Returns a ServiceConsumerResult with pool for potential sharing.
    """
    queue_name = f"server.bort_{settings.VEHICLE_ID}.cdc_{config.service_name}.dst"
    pool = await asyncpg.create_pool(config.db_settings.POSTGRES_URL)
    assert pool is not None
    registry = ServiceRegistry(f"{config.service_name}_service", pool)
    factory = config.factory_class(registry)

    outbox_writer: OutboxWriter | None = None
    if config.outbox_rules:
        outbox_writer = OutboxWriter(config.outbox_rules)
        await outbox_writer.setup(pool)

    applier = AggregateApplier(
        factory,
        config.service_name,
        queue_name,
        outbox_writer=outbox_writer,
    )
    await applier.setup()
    consumer = AmqpConsumer(
        service_name=config.service_name,
        queue_name=queue_name,
        handler=applier,
        prefetch_count=settings.PREFETCH_COUNT,
    )
    return ServiceConsumerResult(
        consumer=consumer,
        pool=pool,
        has_outbox=bool(config.outbox_rules),
    )


__all__ = ["ServiceConsumerConfig", "ServiceConsumerResult", "create_service_consumer"]
