"""MQTT-клиент телеметрии транспорта: GPS, скорость, вес, топливо, теги, trip-service события.
Топики, парсинг payload и обработка — в одном модуле.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, ClassVar, Optional

from sqlalchemy import and_, func, select

from app.core.mqtt.base import MQTTClientBase
from app.core.redis.vehicle.vehicle_places import save_vehicle_place
from app.core.redis.vehicle.vehicle_state import save_vehicle_state
from app.core.websocket_client import broadcast_to_room_sync, get_event_loop
from app.models.database import GraphNode, Horizon, Place, VehicleLocation
from app.utils.coordinates import transform_gps_to_canvas
from config.database import AsyncSessionLocal
from config.settings import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

TOPICS = [
    "truck/+/sensor/gps/ds",
    "truck/+/sensor/speed/ds",
    "truck/+/sensor/weight/ds",
    "truck/+/sensor/fuel/ds",
    "truck/+/sensor/tag/events",
    "truck/+/trip-service/events",
]


def get_vehicle_id_from_topic(topic_parts: list, msg: Any) -> str | None:
    """Формат: truck/{vehicle_id}/sensor/{type}/... или truck/{vehicle_id}/trip-service/events."""
    if len(topic_parts) >= 3 and topic_parts[0] == "truck":
        return topic_parts[1]
    logger.warning("Unexpected topic format: %s", getattr(msg, "topic", topic_parts))
    return None


def get_sensor_type(topic_parts: list, msg: Any) -> str | None:
    """Тип топика: sensor (gps, speed, weight, fuel, tag) или trip-service event."""
    if len(topic_parts) >= 4 and topic_parts[2] == "sensor":
        return topic_parts[3]
    if len(topic_parts) >= 4 and topic_parts[2] == "trip-service" and topic_parts[3] == "events":
        return "event"
    logger.warning("Unknown topic format: %s", getattr(msg, "topic", topic_parts))
    return None


def parsing_event(payload: dict) -> tuple[dict, float, dict]:
    """Event-сообщения: данные на верхнем уровне."""
    data = payload
    metadata: dict = {}
    timestamp = payload.get("timestamp", time.time())
    return data, timestamp, metadata


def parsing_sensor(payload: dict) -> tuple[dict, float, dict]:
    """Sensor-сообщения: структура data/metadata."""
    data = payload.get("data", {})
    metadata = payload.get("metadata", {})
    timestamp = metadata.get("timestamp", time.time())
    return data, timestamp, metadata


def broadcast_vehicle_update(location_update: dict) -> None:
    """Отправка обновления позиции транспорта через WebSocket (вызов из MQTT callback)."""
    try:
        message = {"type": "vehicle_location_update", "data": location_update}
        broadcast_to_room_sync("vehicle_tracking", message)
    except Exception as e:
        logger.error("Error broadcasting vehicle update: %s", e)


async def save_vehicle_location_async(
    vehicle_id: str,
    lat: float,
    lon: float,
    height: float | None,
    timestamp: float,
) -> None:
    """Сохранение местоположения транспортного средства в БД (async)."""
    try:
        async with AsyncSessionLocal() as db:
            horizon_id: int | None = None
            if height is not None:
                try:
                    horizon_result = await db.execute(
                        select(Horizon.id).where(Horizon.height == height),
                    )
                    horizon_id = horizon_result.scalar_one_or_none()
                except Exception:
                    logger.error(
                        "save_vehicle_location_async: no horizon with current height %s",
                        height,
                    )
                    horizon_id = None

            five_seconds_ago = datetime.fromtimestamp(timestamp) - timedelta(seconds=5)
            point = func.ST_SetSRID(
                func.ST_MakePoint(
                    float(lon),
                    float(lat),
                    float(height if height is not None else 0.0),
                ),
                4326,
            )
            existing_result = await db.execute(
                select(VehicleLocation)
                .where(
                    and_(
                        VehicleLocation.vehicle_id == vehicle_id,
                        VehicleLocation.timestamp >= five_seconds_ago,
                        VehicleLocation.geometry == point,
                        VehicleLocation.horizon_id.is_(horizon_id)
                        if horizon_id is None
                        else VehicleLocation.horizon_id == horizon_id,
                    ),
                )
                .order_by(VehicleLocation.id.desc())
                .limit(1),
            )
            existing_location = existing_result.scalars().first()
            if existing_location:
                logger.debug("Duplicate location for %s, skipping save", vehicle_id)
                return

            vehicle_location = VehicleLocation(
                vehicle_id=vehicle_id,
                horizon_id=horizon_id,
                geometry=point,
                timestamp=datetime.fromtimestamp(timestamp),
            )
            db.add(vehicle_location)
            await db.commit()
            logger.debug(
                "Saved vehicle location for %s: horizon_id=%s, geometry=%s",
                vehicle_id,
                horizon_id,
                point,
            )
    except Exception as e:
        logger.error("Error saving vehicle location: %s", e)


def save_vehicle_location(
    vehicle_id: str,
    lat: float,
    lon: float,
    height: float | None,
    timestamp: float,
) -> None:
    """Синхронная обёртка для сохранения местоположения (из MQTT callback)."""
    loop = get_event_loop()
    if loop is None:
        logger.warning("Event loop not set, cannot save vehicle location")
        return
    try:
        asyncio.run_coroutine_threadsafe(
            save_vehicle_location_async(vehicle_id, lat, lon, height, timestamp),
            loop,
        )
    except Exception as e:
        logger.error("Error in save_vehicle_location wrapper: %s", e)


async def _fetch_place_horizon(place_id: int) -> int | None:
    """Получить horizon_id для Place из БД (async)."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(GraphNode.horizon_id)
            .join(Place, Place.node_id == GraphNode.id)
            .where(Place.id == place_id),
        )
        return result.scalar_one_or_none()


def get_place_horizon(place_id: int) -> int | None:
    """Синхронная обёртка для получения horizon_id по place_id.
    Вызывается из MQTT-потока через общий event loop.
    """
    loop = get_event_loop()
    if loop is None:
        logger.warning("Event loop not set, cannot fetch place horizon")
        return None

    try:
        future = asyncio.run_coroutine_threadsafe(
            _fetch_place_horizon(place_id),
            loop,
        )
        return future.result(timeout=2.0)
    except Exception as e:
        logger.error("Error fetching place horizon for %s: %s", place_id, e)
        return None


class GraphVehicleMQTTClient(MQTTClientBase):
    """MQTT-клиент для телеметрии транспорта: GPS, скорость, вес,
    топливо, теги, trip-service события. Синглтон.
    """

    _instance: ClassVar[Optional["GraphVehicleMQTTClient"]] = None

    @classmethod
    def get_instance(cls) -> Optional["GraphVehicleMQTTClient"]:
        """Вернуть единственный экземпляр или None, если ещё не создан/уже остановлен."""
        return cls._instance

    @classmethod
    def get_or_create(cls) -> "GraphVehicleMQTTClient":
        """Вернуть единственный экземпляр, создав его при первом вызове."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Остановить клиент и сбросить синглтон (для stop_mqtt_client)."""
        if cls._instance is not None:
            cls._instance.stop()
            cls._instance = None

    def __init__(self) -> None:
        super().__init__(
            host=settings.nanomq_host,
            port=settings.nanomq_mqtt_port,
            keepalive=60,
            username=os.getenv("MQTT_USERNAME") or None,
            password=os.getenv("MQTT_PASSWORD") or None,
            topics=TOPICS,
        )
        self.vehicle_telemetry: dict = {}

    def handle_message(self, topic: str, payload: bytes) -> None:
        topic_parts = topic.split("/")
        msg = SimpleNamespace(topic=topic)

        vehicle_id_from_topic = get_vehicle_id_from_topic(topic_parts, msg)
        if vehicle_id_from_topic is None:
            return

        sensor_type = get_sensor_type(topic_parts, msg)
        if sensor_type is None:
            return

        try:
            payload_str = payload.decode("utf-8")
            payload_data = json.loads(payload_str)
        except (ValueError, json.JSONDecodeError) as e:
            logger.error("Failed to parse JSON payload: %s", e)
            return

        logger.info(
            "[MQTT] Received %s message from topic '%s' for vehicle %s",
            sensor_type,
            topic,
            vehicle_id_from_topic,
        )
        logger.debug("Message payload: %s", payload_data)

        if sensor_type == "event":
            data, timestamp, metadata = parsing_event(payload_data)
        else:
            data, timestamp, metadata = parsing_sensor(payload_data)

        if vehicle_id_from_topic not in self.vehicle_telemetry:
            self.vehicle_telemetry[vehicle_id_from_topic] = {}

        cache = self.vehicle_telemetry[vehicle_id_from_topic]

        if sensor_type == "gps":
            self._handle_gps(vehicle_id_from_topic, data, timestamp, cache)
        elif sensor_type == "speed":
            speed = data.get("speed")
            if speed is not None:
                cache["speed"] = speed
                logger.debug("Updated speed for %s: %s km/h", vehicle_id_from_topic, speed)
        elif sensor_type == "weight":
            weight = data.get("weight")
            if weight is not None:
                cache["weight"] = weight
                logger.debug("Updated weight for %s: %s tonnes", vehicle_id_from_topic, weight)
        elif sensor_type == "fuel":
            fuel = data.get("fuel")
            if fuel is not None:
                cache["fuel"] = fuel
                logger.debug("Updated fuel for %s: %s%%", vehicle_id_from_topic, fuel)
        elif sensor_type == "tag":
            self._handle_tag(vehicle_id_from_topic, data, cache)
        elif sensor_type == "event":
            self._handle_event(vehicle_id_from_topic, payload_data, cache)

    def _handle_gps(
        self,
        vehicle_id: str,
        data: dict,
        timestamp: float,
        cache: dict,
    ) -> None:
        lat = data.get("lat")
        lon = data.get("lon")
        height = data.get("height")

        if lat is None or lon is None:
            logger.warning("Invalid GPS data: lat or lon is null. Skipping message.")
            return

        if height is None:
            height = float(os.getenv("DEFAULT_VEHICLE_HEIGHT", "0"))
            logger.debug(
                "Height is None for %s, using DEFAULT_VEHICLE_HEIGHT=%s",
                vehicle_id,
                height,
            )

        cache["lat"] = lat
        cache["lon"] = lon
        cache["height"] = height
        cache["timestamp"] = timestamp

        save_vehicle_location(vehicle_id, lat, lon, height, timestamp)

        # Обновляем in-memory кэш для SSE стрима прогресса маршрута
        try:
            from app.services.live_vehicle_locations import update as update_live

            update_live(vehicle_id, lat, lon, timestamp)
        except Exception:
            logger.warning(
                "mqtt_graph_vehicles: failed to update live_vehicle_locations cache",
                exc_info=True,
            )

        canvas_x, canvas_y = transform_gps_to_canvas(lat, lon)
        location_update = {
            "vehicle_id": vehicle_id,
            "lat": lat,
            "lon": lon,
            "canvasX": canvas_x,
            "canvasY": canvas_y,
            "height": height,
            "speed": cache.get("speed"),
            "weight": cache.get("weight"),
            "fuel": cache.get("fuel"),
            "tag": cache.get("tag"),
            "state": cache.get("state"),
            "task_id": cache.get("task_id"),
            "trip_type": cache.get("trip_type"),
            "timestamp": timestamp,
        }
        broadcast_vehicle_update(location_update)
        logger.info(
            "Vehicle location update sent: %s at GPS(%.6f, %.6f)"
            " → Canvas(%.2f, %.2f), height=%s, state=%s",
            vehicle_id,
            lat,
            lon,
            canvas_x,
            canvas_y,
            height,
            cache.get("state"),
        )

    def _handle_tag(self, vehicle_id: str, data: dict, cache: dict) -> None:
        logger.info("Processing tag event data: %s", data)
        point_id = data.get("point_id")
        point_name = data.get("point_name")
        point_type = data.get("point_type")
        place_id = data.get("place_id") if data.get("place_id") is not None else point_id

        tag_info = None
        if point_id and point_name:
            tag_info = {
                "point_id": point_id,
                "point_name": point_name,
                "point_type": point_type,
            }
            logger.info("Valid tag found: %s", tag_info)
        else:
            logger.info("Invalid tag data: point_id=%s, point_name=%s", point_id, point_name)

        if place_id is not None and place_id != 0:
            try:
                place_id_int = int(place_id) if not isinstance(place_id, int) else place_id
            except (TypeError, ValueError) as e:
                logger.warning(
                    "Vehicle place bridge: invalid place_id for vehicle %s: %s",
                    vehicle_id,
                    e,
                )
                place_id_int = None

            if place_id_int is not None:
                horizon_val: int | None = get_place_horizon(place_id_int)
                save_vehicle_place(vehicle_id, place_id_int, horizon_val)

        cache["tag"] = tag_info
        logger.info("Updated tag for %s: %s", vehicle_id, tag_info)

    def _handle_event(self, vehicle_id: str, payload: dict, cache: dict) -> None:
        logger.info("Processing trip-service event: %s", payload)
        event_type = payload.get("event_type")
        state = payload.get("state")
        cycle_id = payload.get("cycle_id")
        task_id = payload.get("task_id")
        trip_type = payload.get("trip_type")
        event_timestamp = payload.get("timestamp", time.time())
        point_id = payload.get("point_id")

        cache["last_event_type"] = event_type
        cache["cycle_id"] = cycle_id
        cache["task_id"] = task_id
        cache["trip_type"] = trip_type
        cache["point_id"] = point_id
        cache["timestamp"] = event_timestamp
        if state:
            cache["state"] = state
            try:
                save_vehicle_state(vehicle_id, str(state))  # type: ignore[arg-type]
            except Exception as e:
                logger.warning("Failed to save vehicle state to Redis: %s", e)
            logger.info("[STATE] State updated: %s -> %s", vehicle_id, state)
        else:
            logger.warning(
                "Event %s does not contain state value for %s",
                event_type,
                vehicle_id,
            )

        lat = cache.get("lat")
        lon = cache.get("lon")
        height = cache.get("height")
        if height is None:
            try:
                height = float(os.getenv("DEFAULT_VEHICLE_HEIGHT", "0"))
            except ValueError:
                height = 0.0
            cache["height"] = height

        canvas_x = None
        canvas_y = None
        if lat is not None and lon is not None:
            canvas_x, canvas_y = transform_gps_to_canvas(lat, lon)

        current_state = cache.get("state")
        if current_state:
            logger.info(
                "[WS] Sending state update via WebSocket: %s -> %s",
                vehicle_id,
                current_state,
            )
        else:
            logger.warning("State is None when sending event update for %s", vehicle_id)

        location_update = {
            "vehicle_id": vehicle_id,
            "lat": lat,
            "lon": lon,
            "canvasX": canvas_x,
            "canvasY": canvas_y,
            "height": height,
            "speed": cache.get("speed"),
            "weight": cache.get("weight"),
            "fuel": cache.get("fuel"),
            "tag": cache.get("tag"),
            "state": current_state,
            "task_id": cache.get("task_id"),
            "trip_type": cache.get("trip_type"),
            "timestamp": event_timestamp,
        }
        broadcast_vehicle_update(location_update)
        logger.info(
            "[TELEMETRY] Vehicle telemetry update emitted: %s, state=%s, has_gps=%s, event_type=%s",
            vehicle_id,
            current_state,
            lat is not None and lon is not None,
            event_type,
        )
