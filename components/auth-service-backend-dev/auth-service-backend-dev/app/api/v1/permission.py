from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.database import get_db
from app.models.permission_model import Permission
from app.models.user_model import User
from app.schemas.permission_schema import PermissionCreate, PermissionOut, PermissionCheck
from app.utils.user_util import admin_required, get_current_user, get_current_user_mock, get_admin_user_mock
from app.utils.permission_util import has_permission


router = APIRouter(tags=["permissions"])


# ────────────────────────────────
# Создание разрешения
# ────────────────────────────────
@router.post("/permissions", response_model=PermissionOut)
async def create_permission(
    permission: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    # current_user = Depends(admin_required)
):
    result = await db.execute(select(Permission).filter(Permission.name == permission.name))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Permission already exists")

    new_permission = Permission(
        name=permission.name,
        description=permission.description
    )
    db.add(new_permission)
    await db.commit()
    await db.refresh(new_permission)
    return new_permission


# ────────────────────────────────
# Получение всех разрешений
# ────────────────────────────────
@router.get("/permissions", response_model=List[PermissionOut])
async def get_permissions(
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)
    # current_user = Depends(admin_required)
):
    result = await db.execute(select(Permission))
    permissions = result.scalars().all()
    return permissions


# ────────────────────────────────
# Получение разрешения по id
# ────────────────────────────────
@router.get("/permissions/{permission_id}", response_model=PermissionOut)
async def get_permission(
    permission_id: int,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)
    # current_user = Depends(admin_required)
):
    result = await db.execute(select(Permission).filter(Permission.id == permission_id))
    permission = result.scalar_one_or_none()
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    return permission


# ────────────────────────────────
# Проверка разрешения для пользователя
# ────────────────────────────────
# @router.post("/permissions/check")
# async def check_permission(
#         perm: PermissionCheck,
#         # current_user: User = Depends(get_current_user)
# ):
#     """Check if the current user has a specific permission."""
#     if await has_permission(current_user, perm.permission):
#         return {"has_permission": True}
#     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
#
# @router.get("/permissions/my")
# async def get_my_permissions(current_user: User = Depends(get_current_user)):
#     """Retrieve all permissions for the current user."""
#
#     return {
#         "user_id": current_user.id,
#         "role": current_user.role.name,
#         "permissions": current_user.role.permissions
#     }