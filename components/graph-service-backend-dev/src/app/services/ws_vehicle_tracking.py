"""Сервис для WebSocket отслеживания транспорта"""

import json
import logging

from sqlalchemy import desc, func, select

from app.models.database import VehicleLocation
from config.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class VehicleTrackingWSService:
    """Бизнес-логика для WebSocket отслеживания транспорта."""

    # TODO по всему сервису тянутся вот эти заглушки с 4_truck, их надо будет выпилить
    async def get_current_location(self, vehicle_id: str = "4_truck") -> dict | None:
        """Получить последнее местоположение транспортного средства."""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(
                        VehicleLocation.vehicle_id,
                        VehicleLocation.horizon_id,
                        VehicleLocation.timestamp,
                        func.ST_AsGeoJSON(VehicleLocation.geometry).label("geometry"),
                    )
                    .where(VehicleLocation.vehicle_id == vehicle_id)
                    .order_by(desc(VehicleLocation.timestamp))
                    .limit(1),
                )
                latest_location = result.mappings().first()

                if not latest_location:
                    return None

                return {
                    "vehicle_id": latest_location["vehicle_id"],
                    "horizon_id": latest_location["horizon_id"],
                    "geometry": json.loads(latest_location["geometry"])
                    if latest_location["geometry"]
                    else None,
                    "timestamp": latest_location["timestamp"].isoformat(),
                }
        except Exception as e:
            logger.error(f"Error getting current location: {e}")
            raise


vehicle_tracking_ws_service = VehicleTrackingWSService()
