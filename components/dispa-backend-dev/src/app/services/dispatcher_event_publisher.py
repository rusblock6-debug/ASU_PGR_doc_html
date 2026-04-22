"""Публикация событий при изменении статутса борта диспечером в MQTT."""

from typing import Any

from loguru import logger


async def publish_dispatcher_event(
    vehicle_id: int,
    event_data: dict[str, Any],
) -> None:
    r"""Только в серверном режиме. Публикует в mqtt топик dispatcher/{vehicle_id}/changes сообытие о смене.

    последнего статуса борта \ создании нового статуса борта на КРВ.
    """
    try:
        from app.services.event_handlers import mqtt_client

        if not mqtt_client:
            logger.warning(
                "MQTT client not initialized, skipping event publication",
            )
            return

        if hasattr(event_data, "model_dump"):
            payload = event_data.model_dump(mode="json")
        elif hasattr(event_data, "dict"):
            payload = event_data.dict()
        else:
            payload = event_data

        topic = f"dispatcher/{vehicle_id}/changes"

        await mqtt_client.publish(topic, payload)

    except Exception as e:
        logger.error(
            "Failed to publish trip event",
            error=str(e),
            exc_info=True,
        )
