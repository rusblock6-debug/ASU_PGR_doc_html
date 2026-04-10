"""Minio events module."""

from typing import Annotated

from fast_depends import Depends
from faststream.rabbit import RabbitMessage, RabbitQueue, RabbitRouter
from loguru import logger

from src.app.controller import EkiperEventsController, GpsDataController
from src.app.factory import Factory
from src.app.scheme.minio.minio_event import MinioEvent, MinioEventType

router = RabbitRouter()


def is_ekiper_event(event: MinioEvent) -> bool:
    """Is ekiper event?"""
    return "ekiper" in event.key and "events" in event.key


def is_gps_event(event: MinioEvent) -> bool:
    """Is GPS data event?"""
    return "ekiper" in event.key and "gps" in event.key


def is_trip_service_event(event: MinioEvent) -> bool:
    """Is trip_service event?"""
    return "trip_service" in event.key


@router.subscriber(RabbitQueue("minio-events", durable=True))
async def get_minio_file(
    msg: RabbitMessage,
    ekiper_events_controller: Annotated[
        EkiperEventsController,
        Depends(Factory.get_ekiper_events_controller),
    ],
    gps_data_controller: Annotated[
        GpsDataController,
        Depends(Factory.get_gps_data_controller),
    ],
) -> None:
    """Общая очередь для s3 файлов от dump-service."""
    event = MinioEvent.model_validate_json(msg.body)
    if event.event_name == MinioEventType.UNKNOWN:
        return

    # TODO: тут minio присылает лист рекордов,
    #  якобы может несколько файлов прилететь надо будет проверить.

    default_record = event.records[0]

    if is_ekiper_event(event):
        await ekiper_events_controller.load(
            event.key,
            default_record.s3.object.e_tag,
            default_record.s3.object.key,
        )
    elif is_gps_event(event):
        await gps_data_controller.load(
            event.key,
            default_record.s3.object.e_tag,
            default_record.s3.object.key,
        )
    elif is_trip_service_event(event):
        pass
    else:
        logger.info("skip file {file}", file=event.key)
