"""Statuses endpoints."""

from typing import Any

from auth_lib import Action, Permission, require_permission
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.statuses import AnalyticCategoryEnum
from app.schemas.statuses import (
    StatusCreate,
    StatusListResponse,
    StatusResponse,
    StatusUpdate,
)
from app.services import StatusService
from app.utils.dependencies import get_db_session

router = APIRouter(prefix="/statuses", tags=["statuses"])


def get_status_service(db: AsyncSession = Depends(get_db_session)) -> StatusService:
    """Dependency для получения StatusService."""
    return StatusService(db)


@router.get(
    "/analytic-categories",
    response_model=list[dict[str, Any]],
    dependencies=[Depends(require_permission((Permission.STATUSES, Action.VIEW)))],
)
async def list_analytic_categories(
    page: int | None = Query(
        None,
        ge=1,
        description="Номер страницы (опционально, всегда возвращает все категории)",
    ),
    size: int | None = Query(
        None,
        ge=1,
        le=100,
        description="Размер страницы (опционально, всегда возвращает все категории)",
    ),
) -> list[dict[str, Any]]:
    """Получить список аналитических категорий с отображаемыми названиями.

    Параметры page и size принимаются для консистентности API, но всегда возвращает все категории.
    """
    return [
        {
            "value": category.value,
            "display_name": AnalyticCategoryEnum.get_display_name(category.value),
        }
        for category in AnalyticCategoryEnum
    ]


@router.get(
    "",
    response_model=StatusListResponse,
    dependencies=[
        Depends(
            require_permission(
                (Permission.WORK_TIME_MAP, Action.VIEW),
                (Permission.STATUSES, Action.VIEW),
            ),
        ),
    ],
)
async def list_statuses(
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
    service: StatusService = Depends(get_status_service),
) -> StatusListResponse:
    """Получить список статусов с пагинацией или без неё.

    Если параметры page и size не указаны, возвращает все записи без пагинации.
    """
    result = await service.get_list(page=page, size=size)
    items = [StatusResponse.from_orm_with_display(item) for item in result["items"]]
    return StatusListResponse(
        total=result["total"],
        page=result["page"],
        size=result["size"],
        items=items,
    )


@router.post(
    "",
    response_model=StatusResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission((Permission.STATUSES, Action.EDIT)))],
)
async def create_status(
    data: StatusCreate,
    service: StatusService = Depends(get_status_service),
) -> StatusResponse:
    """Создать новый статус."""
    status_obj = await service.create(data)
    return StatusResponse.from_orm_with_display(status_obj)


@router.get(
    "/{status_id}",
    response_model=StatusResponse,
    dependencies=[Depends(require_permission((Permission.STATUSES, Action.VIEW)))],
)
async def get_status(
    status_id: int,
    service: StatusService = Depends(get_status_service),
) -> StatusResponse:
    """Получить статус по ID."""
    status_obj = await service.get_by_id(status_id)
    if not status_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Статус с ID {status_id} не найден",
        )
    return StatusResponse.from_orm_with_display(status_obj)


@router.get(
    "/by-system-name/{system_name}",
    response_model=StatusResponse,
    dependencies=[Depends(require_permission((Permission.STATUSES, Action.VIEW)))],
)
async def get_status_by_system_name(
    system_name: str,
    service: StatusService = Depends(get_status_service),
) -> StatusResponse:
    """Получить статус по system_name."""
    status_obj = await service.get_by_system_name(system_name)
    if not status_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Статус с system_name '{system_name}' не найден",
        )
    return StatusResponse.from_orm_with_display(status_obj)


@router.put(
    "/{status_id}",
    response_model=StatusResponse,
    dependencies=[Depends(require_permission((Permission.STATUSES, Action.EDIT)))],
)
async def update_status(
    status_id: int,
    data: StatusUpdate,
    service: StatusService = Depends(get_status_service),
) -> StatusResponse:
    """Обновить статус."""
    status_obj = await service.update(status_id, data)
    if not status_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Статус с ID {status_id} не найден",
        )
    return StatusResponse.from_orm_with_display(status_obj)


@router.delete(
    "/{status_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission((Permission.STATUSES, Action.EDIT)))],
)
async def delete_status(
    status_id: int,
    service: StatusService = Depends(get_status_service),
) -> None:
    """Удалить статус."""
    deleted = await service.delete(status_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Статус с ID {status_id} не найден",
        )
    return None
