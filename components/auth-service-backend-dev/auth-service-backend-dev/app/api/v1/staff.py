from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.schemas.common import StrList
from app.services.staff import (
    get_staff_list,
    create_staff_row,
    update_staff_by_id,
    get_staff_row_by_id,
    delete_staff_by_id,
    get_positions_staff,
    get_department_staff
)
from app.utils.user_util import admin_required, get_current_user
from app.schemas.staff_schema import (
    StaffListResponse,
    StaffCreate,
    StaffUpdate,
    StaffResponse
)


router = APIRouter(tags=["staff"])


@router.get("/staff", response_model=StaffListResponse)
async def get_staff(
        db: AsyncSession = Depends(get_db),
        page: Optional[int] = Query(None, ge=1, description="Номер страницы (опционально, если не указан - возвращает все записи)"),
        size: Optional[int] = Query(None, ge=1, le=100, description="Размер страницы (опционально, если не указан - возвращает все записи)"),
        # current_user: User = Depends(get_current_user)
):
    return await get_staff_list(db, page, size)


@router.post("/staff", status_code=201)
async def create_staff(
        staff: StaffCreate,
        db: AsyncSession = Depends(get_db),
        # current_user: User = Depends(get_current_user)
        # current_user: User = Depends(admin_required)
):
    try:
        new_staff_id = await create_staff_row(db, staff)
        return {"status": "created", "staff_id": new_staff_id}
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while creating staff: {str(e)}"
        )


@router.get("/staff/position", response_model=StrList)
async def get_staff_positions(
        db: AsyncSession = Depends(get_db),
        # current_user: User = Depends(get_current_user),
        # current_user: User = Depends(admin_required),
):
    try:
        result = await get_positions_staff(db)
        return {"items": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staff/department", response_model=StrList)
async def get_staff_department(
        db: AsyncSession = Depends(get_db),
        # current_user: User = Depends(get_current_user),
        # current_user: User = Depends(admin_required),
):
    try:
        result = await get_department_staff(db)
        return {"items": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/staff/{staff_id}")
async def update_staff(
        staff_id: int,
        staff: StaffUpdate,
        db: AsyncSession = Depends(get_db),
        # current_user: User = Depends(get_current_user)
        # current_user: User = Depends(admin_required)
):
    try:
        await update_staff_by_id(db, staff, staff_id)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Staff member updated successfully", "staff_id": staff_id}



@router.get("/staff/{staff_id}", response_model=StaffResponse)
async def get_staff_by_id(
        staff_id: int,
        db: AsyncSession = Depends(get_db),
        # current_user: User = Depends(get_current_user)
        # current_user: User = Depends(admin_required)
):
    try:
        row = await get_staff_row_by_id(db, staff_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)
        )
    return row


@router.delete("/staff/{staff_id}")
async def delete_staff(
        staff_id: int,
        db: AsyncSession = Depends(get_db),
        # current_user: User = Depends(get_current_user)
        # current_user: User = Depends(admin_required)
):
    try:
        await delete_staff_by_id(db, staff_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)
        )
    return {"status": "deleted", "staff_id": staff_id}
