from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from app.database import get_db
from app.schemas.role_schema import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleListResponse
)
from app.services.role import create_role_rows, get_all_roles, get_role_by_id, update_role_row, delete_role_row
from app.utils.user_util import admin_required, get_current_user

router = APIRouter(tags=["roles"])
logger = logging.getLogger(__name__)


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)
    # current_user: User = Depends(admin_required)
) -> RoleResponse:
    result = await create_role_rows(db, role_data)
    return result

@router.get("/roles", response_model=RoleListResponse)
async def get_roles(
        db: AsyncSession = Depends(get_db),
        page: Optional[int] = Query(None, ge=1, description="Номер страницы (опционально, если не указан - возвращает все записи)"),
        size: Optional[int] = Query(None, ge=1, le=100, description="Размер страницы (опционально, если не указан - возвращает все записи)"),
        # current_user: User = Depends(get_current_user)
):
    try:
        result = await get_all_roles(db, page, size)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"An error occurred while getting list roles: {str(e)}"
        )


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
        role_id: int,
        db: AsyncSession = Depends(get_db),
        # current_user: User = Depends(get_current_user)
):
    try:
        result = await get_role_by_id(db, role_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"An error occurred while getting role {role_id}: {str(e)}"
        )


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_update: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)
    # current_user: User = Depends(admin_required)
):
    try:
        result = await update_role_row(db, role_id, role_update)
        return result
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"An error occurred while updating role {role_id}: {str(e)}"
        )


@router.delete("/roles/{role_id}")
async def delete_role(
        role_id: int,
        db: AsyncSession = Depends(get_db),
        # current_user: User = Depends(get_current_user)
        # current_user: User = Depends(admin_required)
):
    try:
        result = await delete_role_row(db, role_id)
        return result
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"An error occurred while deleting role {role_id}: {str(e)}"
        )
