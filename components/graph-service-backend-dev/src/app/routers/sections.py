"""CRUD операции для участков (sections)"""

import logging

from auth_lib import Action, Permission, require_permission
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.sections import (
    SectionCreate,
    SectionListBulkCreate,
    SectionListBulkUpdate,
    SectionListResponse,
    SectionResponse,
    SectionUpdate,
)
from app.services.sections import section_service
from config.database import get_async_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sections", tags=["Sections"])


@router.get(
    "",
    response_model=SectionListResponse,
    dependencies=[Depends(require_permission((Permission.SECTIONS, Action.VIEW)))],
)
async def get_sections(
    page: int | None = Query(None, ge=1, description="Номер страницы (опционально)"),
    size: int | None = Query(None, ge=1, le=100, description="Размер страницы (опционально)"),
    db: AsyncSession = Depends(get_async_db),
):
    """Получить список всех участков.

    Если параметры page и size не указаны — возвращает все записи.
    Если указан хотя бы один — применяется пагинация.
    """
    try:
        return await section_service.get_sections(db, page, size)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except ValidationError as e:
        logger.error(f"Validation error in get_sections: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}",
        ) from e
    except Exception as e:
        logger.exception(f"Unexpected error in get_sections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


@router.get(
    "/{section_id}",
    response_model=SectionResponse,
    dependencies=[Depends(require_permission((Permission.SECTIONS, Action.VIEW)))],
)
async def get_section(section_id: int, db: AsyncSession = Depends(get_async_db)):
    """Получить участок по ID"""
    try:
        return await section_service.get_section(db, section_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "",
    response_model=SectionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission((Permission.SECTIONS, Action.EDIT)))],
)
async def create_section(section_data: SectionCreate, db: AsyncSession = Depends(get_async_db)):
    """Создать один участок"""
    try:
        return await section_service.create_section(db, section_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/bulk",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission((Permission.SECTIONS, Action.EDIT)))],
)
async def create_sections_bulk(
    bulk_request: SectionListBulkCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """Создать участки (bulk операция)"""
    try:
        return await section_service.create_sections_bulk(db, bulk_request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.patch(
    "/bulk",
    dependencies=[Depends(require_permission((Permission.SECTIONS, Action.EDIT)))],
)
async def patch_sections_bulk(
    bulk_request: SectionListBulkUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    """Обновить участки (bulk операция)"""
    try:
        return await section_service.patch_sections_bulk(db, bulk_request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.patch(
    "/{section_id}",
    response_model=SectionResponse,
    dependencies=[Depends(require_permission((Permission.SECTIONS, Action.EDIT)))],
)
async def patch_section(
    section_id: int,
    update_data: SectionUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    """Обновить одну участок"""
    try:
        return await section_service.patch_section(db, section_id, update_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete(
    "/{section_id}",
    dependencies=[Depends(require_permission((Permission.SECTIONS, Action.EDIT)))],
)
async def delete_section(section_id: int, db: AsyncSession = Depends(get_async_db)):
    """Удалить участок"""
    try:
        return await section_service.delete_section(db, section_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
