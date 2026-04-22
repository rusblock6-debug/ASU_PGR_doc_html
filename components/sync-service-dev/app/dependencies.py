from collections.abc import AsyncGenerator, Sequence
from itertools import cycle
from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends, HTTPException, status
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialWithJitterBackoff

from app.autorepub.config_manager import AutorepubConfigManager
from app.autorepub.mqtt_manager import AutorepubMQTTManager
from app.autorepub.rabbitmq_manager import AutorepubRabbitMQManager
from app.coordination.coordinator import OwnershipCoordinator
from app.delivery.delivery_manager import DeliveryManager
from app.delivery.retry_manager import RetryManager
from app.mqtt.client import MQTTClient
from app.protocol.disassembler import Disassembler
from app.protocol.reassembler import Reassembler
from app.settings import settings
from app.state.events_store import EventsStore
from app.state.locks_store import LocksStore


class ServiceContainer:
    """Container for service dependencies."""

    def __init__(self) -> None:
        """Initialize container."""
        self.mqtt_client: MQTTClient | None = None
        self.retry_manager: RetryManager | None = None
        self.reassembler: Reassembler | None = None
        self.locks_store: LocksStore | None = None
        self.events_store: EventsStore | None = None
        self.disassembler: Disassembler | None = None
        self.delivery_manager: DeliveryManager | None = None
        self.autorepub_mqtt_client: MQTTClient | None = None
        self.autorepub_config_manager: AutorepubConfigManager | None = None
        self.autorepub_mqtt_manager: AutorepubMQTTManager | None = None
        self.autorepub_rabbitmq_manager: AutorepubRabbitMQManager | None = None
        self.coordinator: OwnershipCoordinator | None = None


# Global container instance
_services = ServiceContainer()


def get_mqtt_client() -> MQTTClient:
    """Dependency: Get MQTT client."""
    if not _services.mqtt_client:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Service not initialized: MQTTClient")
    return _services.mqtt_client


def get_retry_manager() -> RetryManager:
    """Dependency: Get retry manager."""
    if not _services.retry_manager:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Service not initialized: RetryManager")
    return _services.retry_manager


def get_reassembler() -> Reassembler:
    """Dependency: Get reassembler."""
    if not _services.reassembler:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Service not initialized: Reassembler")
    return _services.reassembler


def get_locks_store() -> LocksStore:
    """Dependency: Get locks store."""
    if not _services.locks_store:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Service not initialized: LocksStore")
    return _services.locks_store


def get_events_store() -> EventsStore:
    """Dependency: Get events store."""
    if not _services.events_store:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Service not initialized: EventsStore")
    return _services.events_store


def get_disassembler() -> Disassembler:
    """Dependency: Get disassembler."""
    if not _services.disassembler:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Service not initialized: Disassembler")
    return _services.disassembler


def get_delivery_manager() -> DeliveryManager:
    """Dependency: Get delivery manager."""
    if not _services.delivery_manager:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Service not initialized: DeliveryManager")
    return _services.delivery_manager


def get_autorepub_mqtt_client() -> MQTTClient:
    """Dependency: Get MQTT client."""
    if not _services.autorepub_mqtt_client:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Service not initialized: MQTTClient")
    return _services.autorepub_mqtt_client


def get_autorepub_config_manager() -> AutorepubConfigManager:
    """Dependency: Get autorepub config manager."""
    if not _services.autorepub_config_manager:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Service not initialized: AutorepubConfigManager")
    return _services.autorepub_config_manager


def get_autorepub_mqtt_manager() -> AutorepubMQTTManager:
    """Dependency: Get autorepub MQTT manager."""
    if not _services.autorepub_mqtt_manager:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Service not initialized: AutorepubMQTTManager")
    return _services.autorepub_mqtt_manager


def get_autorepub_rabbitmq_manager() -> AutorepubRabbitMQManager:
    """Dependency: Get autorepub RabbitMQ manager."""
    if not _services.autorepub_rabbitmq_manager:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Service not initialized: AutorepubRabbitMQManager")
    return _services.autorepub_rabbitmq_manager


def get_coordinator() -> OwnershipCoordinator:
    """Dependency: Get OwnershipCoordinator."""
    if not _services.coordinator:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Service not initialized: OwnershipCoordinator")
    return _services.coordinator


# FIXME: builtin retry mechanics does not encompass initial connection failures
_redis_pool = redis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=10,
    socket_timeout=2,
    retry_on_timeout=True,
    retry=Retry(
        backoff=ExponentialWithJitterBackoff(base=0.1, cap=10),
        retries=10,
    ),
    decode_responses=False,
)


async def get_redis_client() -> AsyncGenerator[redis.Redis, None]:
    redis_client = redis.Redis(connection_pool=_redis_pool)
    try:
        yield redis_client
    finally:
        await redis_client.aclose()


# Type aliases for cleaner route signatures
MQTTClientDep = Annotated[MQTTClient, Depends(get_mqtt_client)]
RetryManagerDep = Annotated[RetryManager, Depends(get_retry_manager)]
ReassemblerDep = Annotated[Reassembler, Depends(get_reassembler)]
LocksStoreDep = Annotated[LocksStore, Depends(get_locks_store)]
EventsStoreDep = Annotated[EventsStore, Depends(get_events_store)]
DisassemblerDep = Annotated[Disassembler, Depends(get_disassembler)]
DeliveryManagerDep = Annotated[DeliveryManager, Depends(get_delivery_manager)]
AutorepubMQTTClientDep = Annotated[MQTTClient, Depends(get_autorepub_mqtt_client)]
AutorepubConfigManagerDep = Annotated[AutorepubConfigManager, Depends(get_autorepub_config_manager)]
AutorepubMQTTManagerDep = Annotated[AutorepubMQTTManager, Depends(get_autorepub_mqtt_manager)]
AutorepubRabbitMQManagerDep = Annotated[AutorepubRabbitMQManager, Depends(get_autorepub_rabbitmq_manager)]
OwnershipCoordinatorDep = Annotated[OwnershipCoordinator, Depends(get_coordinator)]
RedisClientDep = Annotated[redis.Redis, Depends(get_redis_client)]


class CycleService:

    def __init__(self) -> None:
        self.cycles_dict: dict[str, cycle] = {}

    def init_cycle(self, key: str, base_sequence: Sequence[bool]) -> None:
        if key not in self.cycles_dict:
            self.cycles_dict[key] = cycle(base_sequence)

    def __call__(self, key: str) -> bool:
        return next(self.cycles_dict[key])


_cycle_service = CycleService()
