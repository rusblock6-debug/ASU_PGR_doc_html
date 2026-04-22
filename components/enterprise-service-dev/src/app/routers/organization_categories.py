"""Organization Categories endpoints."""

from typing import Any

from auth_lib import Action, Permission, require_permission
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.statuses import (
    OrganizationCategoryCreate,
    OrganizationCategoryListResponse,
    OrganizationCategoryResponse,
    OrganizationCategoryUpdate,
)
from app.services import OrganizationCategoryService
from app.utils.dependencies import get_db_session

router = APIRouter(prefix="/organization-categories", tags=["organization-categories"])


def get_category_service(
    db: AsyncSession = Depends(get_db_session),
) -> OrganizationCategoryService:
    """Dependency для получения OrganizationCategoryService."""
    return OrganizationCategoryService(db)


@router.get(
    "",
    response_model=OrganizationCategoryListResponse,
    dependencies=[Depends(require_permission((Permission.STATUSES, Action.VIEW)))],
)
async def list_organization_categories(
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
    service: OrganizationCategoryService = Depends(get_category_service),
) -> dict[str, Any]:
    """Получить список организационных категорий с пагинацией или без неё.

    Если параметры page и size не указаны, возвращает все записи без пагинации.
    """
    return await service.get_list(page=page, size=size)


@router.post(
    "",
    response_model=OrganizationCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission((Permission.STATUSES, Action.EDIT)))],
)
async def create_organization_category(
    data: OrganizationCategoryCreate,
    service: OrganizationCategoryService = Depends(get_category_service),
) -> Any:
    """Создать новую организационную категорию."""
    # Проверяем уникальность имени
    existing = await service.get_by_name(data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Категория с названием '{data.name}' уже существует",
        )
    return await service.create(data)


@router.get(
    "/{category_id}",
    response_model=OrganizationCategoryResponse,
    dependencies=[Depends(require_permission((Permission.STATUSES, Action.VIEW)))],
)
async def get_organization_category(
    category_id: int,
    service: OrganizationCategoryService = Depends(get_category_service),
) -> Any:
    """Получить организационную категорию по ID."""
    category = await service.get_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Категория с ID {category_id} не найдена",
        )
    return category


@router.put(
    "/{category_id}",
    response_model=OrganizationCategoryResponse,
    dependencies=[Depends(require_permission((Permission.STATUSES, Action.EDIT)))],
)
async def update_organization_category(
    category_id: int,
    data: OrganizationCategoryUpdate,
    service: OrganizationCategoryService = Depends(get_category_service),
) -> Any:
    """Обновить организационную категорию."""
    # Проверяем уникальность нового имени
    if data.name:
        existing = await service.get_by_name(data.name)
        if existing and existing.id != category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Категория с названием '{data.name}' уже существует",
            )

    category = await service.update(category_id, data)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Категория с ID {category_id} не найдена",
        )
    return category


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission((Permission.STATUSES, Action.EDIT)))],
)
async def delete_organization_category(
    category_id: int,
    service: OrganizationCategoryService = Depends(get_category_service),
) -> None:
    """Удалить организационную категорию."""
    deleted = await service.delete(category_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Категория с ID {category_id} не найдена",
        )
    return None
