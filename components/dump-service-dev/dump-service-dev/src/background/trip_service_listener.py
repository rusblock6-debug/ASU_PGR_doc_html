"""Background listener that reacts to trip-service MQTT events."""

from multiprocessing import Process

from fastapi import Depends
from loguru import logger
from paho.mqtt import client as mqtt_client

from src.app.controller import TripController
from src.app.exception import DumpIsAlreadyGenerated
from src.app.factory import Factory
from src.app.scheme import mqtt_event
from src.app.type import TripStatus
from src.core.config import get_settings
from src.core.mqtt_broker import MQTTApp, MQTTRouter

settings = get_settings()
router = MQTTRouter()


@router.subscriber(f"/truck/{settings.TRUCK_ID}/trip-service/events")
async def trip_events(
    payload: mqtt_event.TripEvent,
    _topic: str,
    _qos: int,
    _msg: mqtt_client.MQTTMessage,
    trip_controller: TripController = Depends(Factory().get_trip_controller),
) -> None:
    """Handle MQTT events and trigger dump generation when needed."""
    match payload.event_type:
        case TripStatus.TRIP_COMPLETED:
            logger.info(
                "Trip completed event received, generating dump",
                cycle_id=payload.cycle_id,
            )
            try:
                await trip_controller.generate_dump_parquet(trip_id=payload.cycle_id)
            except DumpIsAlreadyGenerated:
                logger.error("Dump for trip_id={trip_id} already exists", trip_id=payload.cycle_id)

        case _:
            logger.debug(
                "Trip event '{event_type}' ignored",
                event_type=payload.event_type,
            )


def _setup_mqtt_app() -> None:
    app = MQTTApp(client_prefix="trip-service-listener")
    app.include_router(router)
    app.setup()


def _worker() -> None:
    logger.info("Launching uploader worker with NanoMQ integration")
    _setup_mqtt_app()


def create_trip_service_listener() -> Process:
    """Create a worker process that listens for trip events.

    The worker subscribes to MQTT topics and triggers dump generation on events.
    """
    return Process(target=_worker, name="trip-service-listener")
