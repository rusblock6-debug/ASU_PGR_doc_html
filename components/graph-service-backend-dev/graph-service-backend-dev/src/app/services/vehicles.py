"""Сервис для работы с транспортными средствами (vehicles)."""

import logging

from app.core.redis.vehicle import PLACES_SUFFIX, REDIS_KEY_PREFIX, STATE_SUFFIX
from app.core.redis.vehicle.vehicle_places import get_all_vehicle_places, get_vehicle_place
from app.core.redis.vehicle.vehicle_speed import get_vehicle_speed
from app.core.redis.vehicle.vehicle_state import get_all_vehicle_states, get_vehicle_state
from app.core.redis.vehicle.vehicle_weight import get_vehicle_weight
from app.schemas.vehicles import (
    VehiclePlaceItem,
    VehiclePlacesListResponse,
    VehiclePopupResponse,
    VehicleStatusItem,
    VehicleStatusListResponse,
)
from app.services.api.trip_service import (
    APITripService,
    TripStatusRouteEnum,
)

logger = logging.getLogger(__name__)


class Vehicle:
    @staticmethod
    async def get_list_vehicles_places() -> VehiclePlacesListResponse:
        """Запрашивает у Redis хеши graph-service:vehicle:*
        и возвращает список мест и горизонтов по подвижному оборудованию.
        """
        try:
            raw = get_all_vehicle_places()
            items: list[VehiclePlaceItem] = []
            prefix_len = len(REDIS_KEY_PREFIX)
            for redis_key, data in raw.items():
                if not data:
                    continue
                if redis_key.startswith(REDIS_KEY_PREFIX) and redis_key.endswith(PLACES_SUFFIX):
                    vehicle_id_str = redis_key[prefix_len : -len(PLACES_SUFFIX)]
                else:
                    vehicle_id_str = (
                        redis_key[prefix_len:]
                        if redis_key.startswith(REDIS_KEY_PREFIX)
                        else redis_key
                    )
                place_id = data.get("place_id")
                horizon_id = data.get("horizon")
                if place_id is None or horizon_id is None:
                    continue

                try:
                    vehicle_id = int(vehicle_id_str)
                except (TypeError, ValueError):
                    logger.debug("Skipping non-numeric vehicle_id %s", vehicle_id_str)
                    continue

                items.append(
                    VehiclePlaceItem(
                        vehicle_id=vehicle_id,
                        place_id=int(place_id),
                        horizon_id=int(horizon_id),
                    ),
                )
        except Exception as e:
            logger.error(
                "Failed to get vehicle places",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise
        return VehiclePlacesListResponse(items=items)

    @staticmethod
    async def get_list_vehicles_states() -> VehicleStatusListResponse:
        """Запрашивает у Redis ключи graph-service:vehicle:*
        и возвращает список state по подвижному оборудованию.
        """
        try:
            raw = get_all_vehicle_states()
            items: list[VehicleStatusItem] = []
            prefix_len = len(REDIS_KEY_PREFIX)
            for redis_key, state in raw.items():
                if state is None or state == "":
                    continue
                if redis_key.startswith(REDIS_KEY_PREFIX) and redis_key.endswith(STATE_SUFFIX):
                    vehicle_id_str = redis_key[prefix_len : -len(STATE_SUFFIX)]
                else:
                    vehicle_id_str = (
                        redis_key[prefix_len:]
                        if redis_key.startswith(REDIS_KEY_PREFIX)
                        else redis_key
                    )
                try:
                    vehicle_id = int(vehicle_id_str)
                except (TypeError, ValueError):
                    logger.debug("Skipping non-numeric vehicle_id %s", vehicle_id_str)
                    continue
                items.append(VehicleStatusItem(vehicle_id=vehicle_id, status=state))
            return VehicleStatusListResponse(items=items)
        except Exception as e:
            logger.error(
                "Failed to get vehicle states",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

    @staticmethod
    def get_vehicles_state(vehicle_id: int) -> str | None:
        """Получить state одного ТС из Redis по vehicle_id. Возвращает None, если записи нет."""
        state = get_vehicle_state(vehicle_id)
        if state is None or state == "":
            return None
        return state

    @staticmethod
    def get_vehicle_speed(vehicle_id: int) -> float | None:
        """Получить скорость одного ТС из Redis по vehicle_id. Возвращает None, если записи нет."""
        speed = get_vehicle_speed(vehicle_id)
        if speed is None:
            return None
        return speed

    @staticmethod
    def get_vehicle_weight(vehicle_id: int) -> float | None:
        """Получить вес одного ТС из Redis по vehicle_id. Возвращает None, если записи нет."""
        weight = get_vehicle_weight(vehicle_id)
        if weight is None:
            return None
        return weight

    @staticmethod
    def get_vehicles_places(vehicle_id: int) -> int | None:
        """Получить place_id одного ТС из Redis по vehicle_id.
        Читает hash graph-service:vehicle:{vehicle_id}:places и возвращает поле place_id.
        """
        data = get_vehicle_place(vehicle_id)
        if not data:
            return None
        place_id = data.get("place_id")
        if place_id is None:
            return None
        try:
            return place_id
        except (TypeError, ValueError):
            logger.debug("Invalid place_id for vehicle_id=%s: %r", vehicle_id, place_id)
            return None

    @staticmethod
    async def get_vehicle_popup(vehicle_id: int) -> VehiclePopupResponse:
        try:
            shift_tasks_payload = await APITripService.get_list_shift_tasks(
                status_route_tasks=[TripStatusRouteEnum.ACTIVE],
                vehicle_ids=[vehicle_id],
            )

            place_start_id: int | None = None
            place_finish_id: int | None = None
            planned_trips_count: int | None = None
            actual_trips_count: int | None = None

            items = (shift_tasks_payload or {}).get("items") or []
            for shift_task in items:
                for rt in shift_task.get("route_tasks") or []:
                    place_start_id = rt.get("place_a_id")
                    place_finish_id = rt.get("place_b_id")
                    planned_trips_count = rt.get("planned_trips_count")
                    actual_trips_count = rt.get("actual_trips_count")

            result = {
                "status_system_name": Vehicle().get_vehicles_state(vehicle_id),
                "place_start_id": place_start_id,
                "place_finish_id": place_finish_id,
                "planned_trips_count": planned_trips_count,
                "actual_trips_count": actual_trips_count,
                "weight": Vehicle().get_vehicle_weight(vehicle_id),
                "speed": Vehicle().get_vehicle_speed(vehicle_id),
                "current_places_id": Vehicle().get_vehicles_places(vehicle_id),
            }
            return VehiclePopupResponse.model_validate(result)
        except Exception as e:
            logger.error(
                "Failed to get vehicle popup",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise


vehicle_service = Vehicle()
