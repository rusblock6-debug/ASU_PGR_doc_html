"""CRUD операции для горизонтов (horizons)"""

import logging

from auth_lib import Action, Permission, require_permission
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.horizons import (
    HorizonCreate,
    HorizonGraphBulkUpsertRequest,
    HorizonListResponse,
    HorizonResponse,
    HorizonUpdate,
)
from app.services.horizons import horizon_service
from config.database import get_async_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/horizons", tags=["Horizons"])


@router.get(
    "",
    response_model=HorizonListResponse,
    dependencies=[
        Depends(
            require_permission(
                (Permission.HORIZONS, Action.VIEW),
                (Permission.PLACES, Action.VIEW),
                (Permission.SECTIONS, Action.VIEW),
            ),
        ),
    ],
)
async def get_horizons(
    page: int | None = Query(None, ge=1, description="Номер страницы (опционально)"),
    size: int | None = Query(None, ge=1, le=100, description="Размер страницы (опционально)"),
    db: AsyncSession = Depends(get_async_db),
):
    """Получить список всех горизонтов.

    Если параметры page и size не указаны — возвращает все записи.
    Если указан хотя бы один — применяется пагинация.
    """
    return await horizon_service.get_horizons(db, page, size)


@router.post(
    "",
    response_model=HorizonResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission((Permission.HORIZONS, Action.EDIT)))],
)
async def create_horizon(level_data: HorizonCreate, db: AsyncSession = Depends(get_async_db)):
    """Создать новый горизонт"""
    try:
        return await horizon_service.create_horizon(db, level_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{horizon_id}",
    response_model=HorizonResponse,
    dependencies=[Depends(require_permission((Permission.HORIZONS, Action.VIEW)))],
)
async def get_horizon(horizon_id: int, db: AsyncSession = Depends(get_async_db)):
    """Получить уровень по ID"""
    try:
        return await horizon_service.get_horizon(db, horizon_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{horizon_id}/graph/count",
    dependencies=[Depends(require_permission((Permission.MAP, Action.VIEW)))],
)
async def get_horizon_objects_count(horizon_id: int, db: AsyncSession = Depends(get_async_db)):
    """Получить количество объектов на горизонте (для предупреждения перед удалением)"""
    try:
        return await horizon_service.get_horizon_objects_count(db, horizon_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.patch(
    "/{horizon_id}",
    response_model=HorizonResponse,
    dependencies=[Depends(require_permission((Permission.HORIZONS, Action.EDIT)))],
)
async def update_horizon(
    horizon_id: int,
    update_data: HorizonUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    """Обновить параметры горизонта (название, высота, цвет, привязка к шахтам)"""
    try:
        return await horizon_service.update_horizon(db, horizon_id, update_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete(
    "/{horizon_id}",
    dependencies=[Depends(require_permission((Permission.HORIZONS, Action.EDIT)))],
)
async def delete_horizon(horizon_id: int, db: AsyncSession = Depends(get_async_db)):
    """Удалить уровень со всеми объектами (каскадное удаление)"""
    try:
        return await horizon_service.delete_horizon(db, horizon_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{horizon_id}/graph",
    dependencies=[Depends(require_permission((Permission.MAP, Action.VIEW)))],
)
async def get_horizon_graph(horizon_id: int, db: AsyncSession = Depends(get_async_db)):
    """Получить полный граф горизонта (узлы, ребра, метки)
    Включает вертикальные ребра между горизонтами
    """
    try:
        return await horizon_service.get_horizon_graph(db, horizon_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/{horizon_id}/graph/bulk-upsert",
    response_model=bool,
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def bulk_upsert_horizon_graph(
    horizon_id: int,
    request: HorizonGraphBulkUpsertRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """Массовое редактирование графа дорог (узлов и ребер) у определенного горизонта"""
    try:
        return await horizon_service.bulk_upsert_horizon_graph(db, horizon_id, request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
