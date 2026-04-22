"""API для транспортных средств (vehicles)."""

from auth_lib import Action, Permission, require_permission
from fastapi import APIRouter, Depends

from app.schemas.vehicles import (
    VehiclePlacesListResponse,
    VehiclePopupResponse,
    VehicleStatusListResponse,
)
from app.services.vehicles import vehicle_service

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


@router.get(
    "/places",
    response_model=VehiclePlacesListResponse,
    dependencies=[Depends(require_permission((Permission.MAP, Action.VIEW)))],
)
async def get_list_vehicles_places() -> VehiclePlacesListResponse:
    """Получение списка последних мест и горизонтов по подвижному оборудованию."""
    return await vehicle_service.get_list_vehicles_places()


@router.get(
    "/state",
    response_model=VehicleStatusListResponse,
    dependencies=[Depends(require_permission((Permission.MAP, Action.VIEW)))],
)
async def get_list_vehicles_states() -> VehicleStatusListResponse:
    """Получение списка state по подвижному оборудованию (из Redis graph-service:vehicle:*)."""
    return await vehicle_service.get_list_vehicles_states()


@router.get(
    "/popup/{vehicle_id}",
    response_model=VehiclePopupResponse,
    dependencies=[Depends(require_permission((Permission.MAP, Action.VIEW)))],
)
async def get_vehicle_popup(vehicle_id: int) -> VehiclePopupResponse:
    """Получить попап для транспортного средства."""
    return await vehicle_service.get_vehicle_popup(vehicle_id)
