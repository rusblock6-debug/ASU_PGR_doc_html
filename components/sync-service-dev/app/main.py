import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.dependencies import _services, get_redis_client
from app.settings import settings

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(asctime)s %(levelname)-7s %(name)-17s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        }
    },
    "loggers": {
        "": {
            "level": settings.log_level,
            "handlers": ["console"],
            "propagate": False,
        },
        "aiormq": {
            "level": "INFO" if settings.log_level == "DEBUG" else settings.log_level,
            "handlers": ["console"],
            "propagate": False,
        },
        "aio_pika": {
            "level": "INFO" if settings.log_level == "DEBUG" else settings.log_level,
            "handlers": ["console"],
            "propagate": False,
        },
    },
}
logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""

    from app.autorepub.config_manager import AutorepubConfigManager
    from app.autorepub.mqtt_manager import AutorepubMQTTManager
    from app.autorepub.rabbitmq_manager import AutorepubRabbitMQManager
    from app.coordination.coordinator import OwnershipCoordinator
    from app.delivery.delivery_manager import DeliveryManager
    from app.delivery.retry_manager import RetryManager
    from app.mqtt.client import MQTTClient
    from app.protocol.disassembler import Disassembler
    from app.protocol.reassembler import Reassembler
    from app.state.events_store import EventsStore
    from app.state.locks_store import LocksStore

    logger.info(f"Starting Sync Service with Instance ID {settings.instance_id}")
    settings.log_dump(_logger=logger)

    try:
        logger.info("Connecting to MQTT broker...")
        _services.mqtt_client = MQTTClient(settings.mqtt_broker_host, settings.mqtt_broker_port)
        await _services.mqtt_client.connect()

        logger.info("Initializing locks store...")
        _services.locks_store = LocksStore()

        logger.info("Initializing events store...")
        _services.events_store = EventsStore()

        logger.info("Initializing messaged store...")
        _services.disassembler = Disassembler()

        logger.info("Initializing retry manager...")
        _services.retry_manager = RetryManager(_services.locks_store, _services.disassembler)

        logger.info("Initializing reassembler...")
        _services.reassembler = Reassembler()

        logger.info("Initializing delivery manager...")
        delivery_redis_client = await anext(get_redis_client())
        _services.delivery_manager = DeliveryManager(
            delivery_redis_client,
            _services.mqtt_client,
            _services.retry_manager,
            _services.reassembler,
            _services.locks_store,
            _services.events_store,
            _services.disassembler,
        )

        logger.info("Connecting to Autorepub MQTT broker...")
        _services.autorepub_mqtt_client = MQTTClient(
            broker_host=settings.autorepub_mqtt_broker_host,
            broker_port=settings.autorepub_mqtt_broker_port,
        )
        await _services.autorepub_mqtt_client.connect()

        logger.info("Initializing autorepub config manager...")
        config_redis_client = await anext(get_redis_client())
        _services.autorepub_config_manager = AutorepubConfigManager(config_redis_client)
        await _services.autorepub_config_manager.load()

        logger.info("Initializing autorepub mqtt manager...")
        _services.autorepub_mqtt_manager = AutorepubMQTTManager(
            _services.autorepub_config_manager,
            _services.delivery_manager,
            _services.autorepub_mqtt_client,
        )
        _services.delivery_manager.on_arrival(_services.autorepub_mqtt_manager._handle_target_message)

        logger.info("Initializing autorepub rabbitmq manager...")
        autorepub_rabbitmq_redis_client = await anext(get_redis_client())
        _services.autorepub_rabbitmq_manager = AutorepubRabbitMQManager(
            autorepub_rabbitmq_redis_client,
            _services.autorepub_config_manager,
            _services.delivery_manager,
            _services.retry_manager,
            _services.events_store,
        )
        _services.delivery_manager.on_arrival(_services.autorepub_rabbitmq_manager._handle_target_message)

        if settings.multi_replica_mode:
            logger.info("Initializing ownership coordinator...")
            coord_redis_client = await anext(get_redis_client())
            _services.coordinator = OwnershipCoordinator(settings.hostname, coord_redis_client)
            # TODO obtain remote instances from proper source (enterprise-service?)
            await _services.coordinator.update_instances(settings.remote_instances_list)
            _services.coordinator.on_acquired(_services.delivery_manager.subscribe_to_instance)
            _services.coordinator.on_acquired(_services.autorepub_mqtt_manager.subscribe_to_instance)
            _services.coordinator.on_acquired(_services.autorepub_rabbitmq_manager.subscribe_to_instance)
            _services.coordinator.on_released(_services.delivery_manager.unsubscribe_from_instance)
            _services.coordinator.on_released(_services.autorepub_mqtt_manager.unsubscribe_from_instance)
            _services.coordinator.on_released(_services.autorepub_rabbitmq_manager.unsubscribe_from_instance)

        logger.info("Starting autorepub mqtt manager...")
        await _services.autorepub_mqtt_manager.start()
        logger.info("Starting autorepub rabbitmq manager...")
        await _services.autorepub_rabbitmq_manager.start()
        logger.info("Starting delivery manager...")
        await _services.delivery_manager.start()
        logger.info("Starting retry manager...")
        await _services.retry_manager.start()
        if _services.coordinator:
            logger.info("Starting ownership coordinator...")
            await _services.coordinator.start()

        logger.info("✓ All components initialized")

        yield

    finally:
        logger.info("Shutting down Sync Service...")

        if _services.coordinator:
            await _services.coordinator.stop()
        if _services.retry_manager:
            await _services.retry_manager.stop()
        if _services.delivery_manager:
            await _services.delivery_manager.stop()
        if _services.autorepub_rabbitmq_manager:
            await _services.autorepub_rabbitmq_manager.stop()
        if _services.autorepub_mqtt_manager:
            await _services.autorepub_mqtt_manager.stop()
        if _services.autorepub_mqtt_client:
            await _services.autorepub_mqtt_client.disconnect()
        if _services.mqtt_client:
            await _services.mqtt_client.disconnect()

        logger.info("✓ Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    from app.api.routes import autorepub, coordination, health

    app = FastAPI(
        title="Sync Service",
        description="Reliable MQTT-based data synchronization service",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Register routers
    app.include_router(health.router)
    app.include_router(autorepub.router)
    app.include_router(coordination.router)

    return app


app = create_app()
