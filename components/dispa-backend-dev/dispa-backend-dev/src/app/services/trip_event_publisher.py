"""Публикация событий рейсов и циклов в MQTT.

Выделен в отдельный модуль для разрыва циклических импортов между
trip_manager, place_remaining, event_handlers и state_machine.
"""

from datetime import UTC, datetime
from typing import Any, cast

from loguru import logger

from app.core.config import settings


async def publish_trip_event(
    event_type: str,
    cycle_id: str | None,
    server_trip_id: str | None,
    trip_type: str | None,
    vehicle_id: str,
    place_id: int,
    state: str | None = None,
    shift_id: str | None = None,
    tag: str | None = None,
    place_remaining_change: dict[str, Any] | None = None,
    history_id: str | None = None,
    event_timestamp: datetime | None = None,
    unloading_timestamp: datetime | None = None,
) -> None:
    """Публикация события рейса/цикла в унифицированный MQTT топик trip-service/events.

    Упрощенный формат:
    - event_type: "trip_started", "trip_completed", "cycle_started", "cycle_completed" или "state_transition"
    - state: состояние машины
    - cycle_id: ID цикла
    - task_id: ID задания
    - shift_id: ID смены (опционально)
    - trip_type: "planned" или "unplanned" (опционально, для циклов может быть None)
    - timestamp: время события
    - place_id: место где произошло событие (place.id)
    - tag: метка локации (point_id)
    - history_id: UUID записи истории (ОБЯЗАТЕЛЬНО для state_transition)
    - place_remaining_change: Данные об изменении остатка места (опционально)
    - unloading_timestamp: Время начала разгрузки (опционально, для trip_completed)
    """
    try:
        from app.services.event_handlers import mqtt_client

        if not mqtt_client:
            logger.warning(
                "MQTT client not initialized, skipping event publication",
                event_type=event_type,
            )
            return

        topic = f"truck/{settings.vehicle_id}/trip-service/events"

        from app.utils import truncate_datetime_to_seconds

        if event_timestamp is not None:
            ts = event_timestamp
        else:
            ts = cast(datetime, truncate_datetime_to_seconds(datetime.now(UTC)))

        event_data: dict[str, Any] = {
            "event_type": event_type,
            "state": state,
            "cycle_id": cycle_id,
            "task_id": str(server_trip_id) if server_trip_id is not None else None,
            "timestamp": ts.timestamp(),
            "place_id": place_id,
            "tag": tag,
        }

        if trip_type:
            event_data["trip_type"] = trip_type

        if shift_id is not None:
            event_data["shift_id"] = shift_id

        if event_type == "state_transition":
            if not history_id:
                logger.error(
                    "Missing required history_id for state_transition event",
                    event_type=event_type,
                    cycle_id=cycle_id,
                    vehicle_id=vehicle_id,
                )
                raise ValueError(
                    f"history_id is required for state_transition events, cycle_id={cycle_id}, vehicle_id={vehicle_id}",
                )
            event_data["history_id"] = history_id

        if place_remaining_change:
            event_data["place_remaining_change"] = place_remaining_change

        if unloading_timestamp is not None:
            event_data["unloading_timestamp"] = unloading_timestamp.isoformat()

        await mqtt_client.publish(topic, event_data)

        logger.info(
            "Trip event published",
            event_type=event_type,
            cycle_id=cycle_id,
            task_id=server_trip_id,
            place_id=place_id,
            tag=tag,
            history_id=history_id,
        )

    except Exception as e:
        logger.error(
            "Failed to publish trip event",
            event_type=event_type,
            error=str(e),
            exc_info=True,
        )
