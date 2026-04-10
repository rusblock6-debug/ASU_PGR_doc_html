"""Background listener that reacts to ekiper MQTT events."""

import asyncio
import signal
import time
from collections.abc import Awaitable, Callable
from contextlib import suppress
from functools import wraps
from multiprocessing import Process
from typing import Concatenate, cast
from uuid import uuid4

from humanfriendly import parse_size
from loguru import logger
from pydantic import BaseModel

from src.app import model
from src.app.factory import Factory
from src.app.scheme.mqtt_event import (
    EkiperFuelDS,
    EkiperFuelEvent,
    EkiperGpsDS,
    EkiperSpeedDS,
    EkiperSpeedEvent,
    EkiperVibroEvent,
    EkiperWeightDS,
    EkiperWeightEvent,
)
from src.app.type import SyncStatus
from src.core.config import get_settings
from src.core.database import db_session
from src.core.database.postgres.dependency import PostgresSession
from src.core.database.postgres.session import reset_session_context, set_session_context
from src.core.dto.scheme.queue import EkiperEvent, EkiperSaveFile
from src.core.mqtt_broker import MQTTApp, MQTTRouter
from src.core.parquet_writter.schema import flatten_model
from src.core.parquet_writter.writter import AsyncParquetWriter

_write_queue = asyncio.Queue[EkiperEvent](maxsize=100_000)
_save_queue = asyncio.Queue[EkiperSaveFile](maxsize=100_000)
router = MQTTRouter()
settings = get_settings()


def queue_ekiper_event[E: BaseModel, **P](
    schema_model: type[BaseModel] | None,
) -> Callable[
    [Callable[Concatenate[E, str, P], Awaitable[None]]],
    Callable[Concatenate[E, str, P], Awaitable[None]],
]:
    """Put handler payloads into the queue while forwarding the call to handler."""

    def decorator(
        func: Callable[Concatenate[E, str, P], Awaitable[None]],
    ) -> Callable[Concatenate[E, str, P], Awaitable[None]]:
        @wraps(func)
        async def wrapper(
            event: E,
            topic: str,
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> None:
            # TODO: временный фикс — данные из двойника неактуальные,
            #  перезаписываем timestamp и идентификатор борта из топика
            event.metadata.timestamp = int(time.time())
            truck_id = topic.split("/")[1]
            if hasattr(event.metadata, "bort"):
                event.metadata.bort = truck_id
            if hasattr(event.metadata, "vehicle_id"):
                event.metadata.vehicle_id = truck_id
            filename = topic.replace("/", "_") + ".parquet"
            row = flatten_model(event)

            await _write_queue.put(
                EkiperEvent(
                    filename=filename,
                    row=row,
                    topic=topic,
                    schema_model=schema_model,
                ),
            )
            await func(event, topic, *args, **kwargs)

        return cast(Callable[Concatenate[E, str, P], Awaitable[None]], wrapper)

    return decorator


@router.subscriber(f"/truck/{settings.TRUCK_ID}/sensor/speed/ds")
@queue_ekiper_event(EkiperSpeedDS)
async def handle_sensor_speed_ds(event: EkiperSpeedDS, topic: str) -> None:
    """Handle speed DS updates from Ekiper sensors."""


@router.subscriber(f"/truck/{settings.TRUCK_ID}/sensor/speed/events")
@queue_ekiper_event(EkiperSpeedEvent)
async def handle_sensor_speed_event(event: EkiperSpeedEvent, topic: str) -> None:
    """Handle speed events from Ekiper sensors."""


@router.subscriber(f"/truck/{settings.TRUCK_ID}/sensor/weight/ds")
@queue_ekiper_event(EkiperWeightDS)
async def handle_sensor_weight_ds(event: EkiperWeightDS, topic: str) -> None:
    """Handle weight DS updates from Ekiper sensors."""


@router.subscriber(f"/truck/{settings.TRUCK_ID}/sensor/weight/events")
@queue_ekiper_event(EkiperWeightEvent)
async def handle_sensor_weight_events(event: EkiperWeightEvent, topic: str) -> None:
    """Handle weight events from Ekiper sensors."""


@router.subscriber(f"/truck/{settings.TRUCK_ID}/sensor/gps/ds")
@queue_ekiper_event(EkiperGpsDS)
async def handle_sensor_gps_ds(event: EkiperGpsDS, topic: str) -> None:
    """Handle GPS DS updates from Ekiper sensors."""


@router.subscriber(f"/truck/{settings.TRUCK_ID}/sensor/fuel/ds")
@queue_ekiper_event(EkiperFuelDS)
async def handle_sensor_fuel_ds(event: EkiperFuelDS, topic: str) -> None:
    """Handle fuel DS updates from Ekiper sensors."""


@router.subscriber(f"/truck/{settings.TRUCK_ID}/sensor/fuel/events")
@queue_ekiper_event(EkiperFuelEvent)
async def handle_sensor_fuel_events(event: EkiperFuelEvent, topic: str) -> None:
    """Handle fuel events from Ekiper sensors."""


@router.subscriber(f"/truck/{settings.TRUCK_ID}/sensor/vibro/events")
@queue_ekiper_event(EkiperVibroEvent)
async def handle_sensor_vibro_events(event: EkiperVibroEvent, topic: str) -> None:
    """Handle vibration events from Ekiper sensors."""


async def save_ekiper_file() -> None:
    """Persist finished parquet file metadata from the done queue."""
    while True:
        try:
            done_file = await _save_queue.get()
            logger.debug("dequeue ekiper file path={path}", path=str(done_file.filepath))
        except asyncio.CancelledError:
            break

        context = set_session_context(str(uuid4()))
        session_dependency = PostgresSession(db_session=db_session)
        try:
            async with session_dependency as session:
                file_controller = Factory().get_file_controller(session)
                await file_controller.create_model(
                    model=model.File(
                        sync_status=SyncStatus.CREATED,
                        path=str(done_file.filepath),
                    ),
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "Failed to store ekiper dump metadata",
                path=str(done_file.filepath),
            )
        finally:
            logger.info("save file={file}", file=str(done_file.filepath.name))
            _save_queue.task_done()
            reset_session_context(context)


def _setup_mqtt_app(*, start_loop: bool = True) -> MQTTApp:
    """Configure MQTT client and optionally start its network loop."""
    app = MQTTApp(client_prefix="ekiper-listener")
    app.include_router(router)
    app.setup(start_loop=start_loop)
    return app


async def _async_worker() -> None:
    parquet_writer = AsyncParquetWriter(
        task_queue=_write_queue,
        done_queue=_save_queue,
        destination=settings.DUMP_STORAGE_DIR / "ekiper",
        batch_size=settings.EKIPER_SETTINGS.BATCH_SIZE,
        flush_interval=settings.EKIPER_SETTINGS.FLUSH_SECONDS_INTERVAL,
        max_file_size_bytes=parse_size(settings.EKIPER_SETTINGS.FILE_ROTATE_SIZE),
    )

    parquet_writer.start()
    saver_task = asyncio.create_task(save_ekiper_file(), name="ekiper-file-saver")

    stop_event = asyncio.Event()

    def _stop() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _stop)

    # Start MQTT network loop in a background thread and keep the handle to stop it later.
    app = _setup_mqtt_app(start_loop=False)
    mqtt_loop_task = asyncio.create_task(asyncio.to_thread(app.run_forever))

    try:
        await stop_event.wait()
    finally:
        logger.info("Disconnecting MQTT client...")
        app.disconnect()

        try:
            await mqtt_loop_task
        except asyncio.CancelledError:
            pass

        logger.info("Waiting for pending events to flush...")
        await _write_queue.join()

        logger.info("Stopping parquet writer...")
        await parquet_writer.stop()

        logger.info("Waiting for saved files to be recorded in DB...")
        await _save_queue.join()

        saver_task.cancel()
        with suppress(asyncio.CancelledError):
            await saver_task


def _worker() -> None:
    logger.info("Launching uploader worker with NanoMQ integration")
    asyncio.run(_async_worker())


def create_ekiper_listener() -> Process:
    """Create a worker process that listens for trip events.

    The worker subscribes to MQTT topics and triggers dump generation on events.
    """
    return Process(target=_worker, name="ekiper-listener")
