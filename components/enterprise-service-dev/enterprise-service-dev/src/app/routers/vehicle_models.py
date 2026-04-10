"""Vehicle Models endpoints.

CRUD операции для моделей транспорта.
"""

from typing import Any

from auth_lib import Action, Permission, require_permission
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.vehicle_models import (
    VehicleModelCreate,
    VehicleModelListResponse,
    VehicleModelResponse,
    VehicleModelUpdate,
)
from app.services import VehicleModelService
from app.utils.dependencies import get_db_session

router = APIRouter(prefix="/vehicle-models", tags=["vehicle-models"])


def get_vehicle_model_service(db: AsyncSession = Depends(get_db_session)) -> VehicleModelService:
    """Dependency для получения VehicleModelService."""
    return VehicleModelService(db)


@router.get(
    "",
    response_model=VehicleModelListResponse,
    dependencies=[Depends(require_permission((Permission.EQUIPMENT, Action.VIEW)))],
)
async def list_vehicle_models(
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
    consist: str | None = Query(None, description="Поиск по подстроке в названии модели"),
    service: VehicleModelService = Depends(get_vehicle_model_service),
) -> dict[str, Any]:
    """Получить список моделей транспорта с пагинацией или без неё.

    Если параметры page и size не указаны, возвращает все записи без пагинации.

    - **page**: номер страницы (опционально)
    - **size**: размер страницы (опционально)
    - **consist**: фильтр по подстроке в названии (регистронезависимый)
    """
    return await service.get_list(page=page, size=size, consist=consist)


@router.post(
    "",
    response_model=VehicleModelResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission((Permission.EQUIPMENT, Action.EDIT)))],
)
async def create_vehicle_model(
    data: VehicleModelCreate,
    service: VehicleModelService = Depends(get_vehicle_model_service),
) -> Any:
    """Создать новую модель транспорта."""
    try:
        return await service.create(data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{model_id}",
    response_model=VehicleModelResponse,
    dependencies=[Depends(require_permission((Permission.EQUIPMENT, Action.VIEW)))],
)
async def get_vehicle_model(
    model_id: int,
    service: VehicleModelService = Depends(get_vehicle_model_service),
) -> Any:
    """Получить модель транспорта по ID."""
    vehicle_model = await service.get_by_id(model_id)
    if not vehicle_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Модель транспорта с ID {model_id} не найдена",
        )
    return vehicle_model


@router.put(
    "/{model_id}",
    response_model=VehicleModelResponse,
    dependencies=[Depends(require_permission((Permission.EQUIPMENT, Action.EDIT)))],
)
async def update_vehicle_model(
    model_id: int,
    data: VehicleModelUpdate,
    service: VehicleModelService = Depends(get_vehicle_model_service),
) -> Any:
    """Обновить модель транспорта.

    Передавайте только те поля, которые нужно изменить.
    """
    try:
        vehicle_model = await service.update(model_id, data)
        if not vehicle_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Модель транспорта с ID {model_id} не найдена",
            )
        return vehicle_model
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete(
    "/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission((Permission.EQUIPMENT, Action.EDIT)))],
)
async def delete_vehicle_model(
    model_id: int,
    service: VehicleModelService = Depends(get_vehicle_model_service),
) -> None:
    """Удалить модель транспорта."""
    deleted = await service.delete(model_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Модель транспорта с ID {model_id} не найдена",
        )
    return None
