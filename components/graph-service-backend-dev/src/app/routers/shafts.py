"""CRUD операции для шахт (shafts)"""

import logging

from auth_lib import Action, Permission, require_permission
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.shafts import (
    ShaftBulkCreateRequest,
    ShaftBulkUpdateRequest,
    ShaftCreate,
    ShaftListResponse,
    ShaftResponse,
    ShaftUpdateSingle,
)
from app.services.shafts import shaft_service
from config.database import get_async_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shafts", tags=["Shafts"])


@router.get(
    "",
    response_model=ShaftListResponse,
    dependencies=[Depends(require_permission((Permission.HORIZONS, Action.VIEW)))],
)
async def get_shafts(
    page: int | None = Query(None, ge=1, description="Номер страницы (опционально)"),
    size: int | None = Query(None, ge=1, le=100, description="Размер страницы (опционально)"),
    db: AsyncSession = Depends(get_async_db),
):
    """Получить список всех шахт.

    Если параметры page и size не указаны — возвращает все записи.
    Если указан хотя бы один — применяется пагинация.
    """
    return await shaft_service.get_shafts(db, page, size)


@router.get(
    "/{shaft_id}",
    response_model=ShaftResponse,
    dependencies=[Depends(require_permission((Permission.HORIZONS, Action.VIEW)))],
)
async def get_shaft(shaft_id: int, db: AsyncSession = Depends(get_async_db)):
    """Получить шахту по ID"""
    try:
        return await shaft_service.get_shaft(db, shaft_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "",
    response_model=ShaftResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission((Permission.HORIZONS, Action.EDIT)))],
)
async def create_shaft(shaft_data: ShaftCreate, db: AsyncSession = Depends(get_async_db)):
    """Создать одну шахту"""
    try:
        return await shaft_service.create_shaft(db, shaft_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/bulk",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission((Permission.HORIZONS, Action.EDIT)))],
)
async def create_shafts_bulk(
    bulk_request: ShaftBulkCreateRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """Создать шахты (bulk операция)"""
    try:
        return await shaft_service.create_shafts_bulk(db, bulk_request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.patch(
    "/bulk",
    dependencies=[Depends(require_permission((Permission.HORIZONS, Action.EDIT)))],
)
async def patch_shafts_bulk(
    bulk_request: ShaftBulkUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """Bulk обновление шахт"""
    try:
        return await shaft_service.patch_shafts_bulk(db, bulk_request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.patch(
    "/{shaft_id}",
    response_model=ShaftResponse,
    dependencies=[Depends(require_permission((Permission.HORIZONS, Action.EDIT)))],
)
async def patch_shaft(
    shaft_id: int,
    update_data: ShaftUpdateSingle,
    db: AsyncSession = Depends(get_async_db),
):
    """Обновить одну шахту"""
    try:
        return await shaft_service.patch_shaft(db, shaft_id, update_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete(
    "/{shaft_id}",
    dependencies=[Depends(require_permission((Permission.HORIZONS, Action.EDIT)))],
)
async def delete_shaft(shaft_id: int, db: AsyncSession = Depends(get_async_db)):
    """Удалить шахту"""
    try:
        return await shaft_service.delete_shaft(db, shaft_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
