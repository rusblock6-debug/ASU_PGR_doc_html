"""Vehicles endpoints."""

from typing import Any

from auth_lib import require_permission
from auth_lib.permissions import Action, Permission
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import (
    VehicleCreate,
    VehicleListResponse,
    VehicleResponse,
    VehicleUpdate,
)
from app.services import VehicleService
from app.utils.dependencies import get_db_session

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def get_vehicle_service(db: AsyncSession = Depends(get_db_session)) -> VehicleService:
    """Dependency для получения VehicleService."""
    return VehicleService(db)


@router.get(
    "",
    response_model=VehicleListResponse,
    dependencies=[
        Depends(
            require_permission(
                (Permission.WORK_TIME_MAP, Action.VIEW),
                (Permission.TRIP_EDITOR, Action.VIEW),
                (Permission.WORK_ORDER, Action.VIEW),
                (Permission.EQUIPMENT, Action.VIEW),
            ),
        ),
    ],
)
async def list_vehicles(
    enterprise_id: int = Query(1),
    vehicle_type: str | None = Query(None),
    page: int | None = Query(
        None,
        ge=1,
        description="Номер страницы (опционально, если не указан - возвращает все записи)",
    ),
    size: int | None = Query(
        None,
        ge=1,
        le=100,
        description="Размер страницы (опционально, если не указан - возвращает все записи)",
    ),
    is_active: bool | None = Query(None),
    service: VehicleService = Depends(get_vehicle_service),
) -> dict[str, Any]:
    """Получить список техники с пагинацией или без неё.

    Если параметры page и size не указаны, возвращает все записи без пагинации.
    """
    return await service.get_list(
        enterprise_id=enterprise_id,
        vehicle_type=vehicle_type,
        is_active=is_active,
        page=page,
        size=size,
    )


@router.post(
    "",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission((Permission.EQUIPMENT, Action.EDIT)))],
)
async def create_vehicle(
    data: VehicleCreate,
    service: VehicleService = Depends(get_vehicle_service),
) -> Any:
    """Создать новый транспорт (ПДМ или ШАС)."""
    return await service.create(data)


@router.get(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    dependencies=[
        Depends(
            require_permission(
                (Permission.WORK_TIME_MAP, Action.VIEW),
                (Permission.TRIP_EDITOR, Action.VIEW),
                (Permission.WORK_ORDER, Action.VIEW),
                (Permission.EQUIPMENT, Action.VIEW),
            ),
        ),
    ],
)
async def get_vehicle(
    vehicle_id: int,
    service: VehicleService = Depends(get_vehicle_service),
) -> Any:
    """Получить транспорт по ID."""
    vehicle = await service.get_by_id(vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Транспорт с ID {vehicle_id} не найден",
        )
    return vehicle


@router.post(
    "/{vehicle_id}/copy",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission((Permission.EQUIPMENT, Action.EDIT)))],
)
async def copy_vehicle(
    vehicle_id: int,
    service: VehicleService = Depends(get_vehicle_service),
) -> Any:
    """Скопировать существующий транспорт.

    Исключаются:
    - id
    - created_at / updated_at
    - serial_number
    """
    try:
        vehicle = await service.copy(vehicle_id)
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Транспорт с ID {vehicle_id} не найден",
            )
        return vehicle
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка при копировании транспорта: {str(e)}",
        ) from e


@router.put(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    dependencies=[Depends(require_permission((Permission.EQUIPMENT, Action.EDIT)))],
)
async def update_vehicle(
    vehicle_id: int,
    data: VehicleUpdate,
    service: VehicleService = Depends(get_vehicle_service),
) -> Any:
    """Обновить транспорт."""
    vehicle = await service.update(vehicle_id, data)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Транспорт с ID {vehicle_id} не найден",
        )
    return vehicle


@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission((Permission.EQUIPMENT, Action.EDIT)))],
)
async def delete_vehicle(
    vehicle_id: int,
    service: VehicleService = Depends(get_vehicle_service),
) -> None:
    """Удалить транспорт (soft delete)."""
    deleted = await service.delete(vehicle_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Транспорт с ID {vehicle_id} не найден",
        )
    return None


@router.get("/{vehicle_id}/speed")
async def get_vehicle_speed(
    vehicle_id: int,
    service: VehicleService = Depends(get_vehicle_service),
) -> dict:
    """
    Получить максимальную скорость модели транспортного средства по его ID.
    Если ТС не найдено или скорость не указана, возвращается 404.
    """
    speed = await service.get_model_max_speed(vehicle_id)
    if speed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Скорость для транспорта с ID {vehicle_id} не найдена (возможно, отсутствует модель или максимальная скорость)",
        )
    return {"speed": speed}
