from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from app.database import get_db

from app.models.user_model import User
from app.models.role_model import Role
from app.schemas.user_schema import UserCreate, UserOut, UserUpdate
from app.utils.user_util import admin_required, get_current_user

router = APIRouter(tags=["users"])

# ────────────────────────────────
# Create user
# ────────────────────────────────
@router.post("/users", response_model=UserOut)
async def create_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)
    # current_user: User = Depends(admin_required)
):
    result = await db.execute(select(User).filter(User.username == user.username))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = User(username=user.username)
    new_user.set_password(user.password)

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


# ────────────────────────────────
# Get all users
# ────────────────────────────────
@router.get("/users", response_model=List[UserOut])
async def get_users(
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(User).options(selectinload(User.role)))
    users = result.scalars().all()
    return users


# ────────────────────────────────
# Get single user
# ────────────────────────────────
@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(User).filter(User.id == user_id).options(selectinload(User.role)))

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# ────────────────────────────────
# Get single user
# ────────────────────────────────
# @router.get("/me")
# async def get_user(
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     result = await db.execute(select(User).filter(User.id == current_user.id))
#     user = result.scalar_one_or_none()
#
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#
#     permissions_data = {}
#     if user.role:
#         perm_list = [perm.name for perm in user.role.permissions]
#         permissions_data["permissions"] = perm_list
#
#
#     user_data = {
#     "id": user.id,
#     "username": user.username,
#     "role": user.role.name if user.role else None,
#     }
#
#     result = {**user_data, **permissions_data}
#
#     return result


# ────────────────────────────────
# Update user
# ────────────────────────────────
@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)
    # current_user: User = Depends(admin_required)
):
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_update.model_dump(exclude_unset=True)

    if "password" in update_data:
        user.set_password(update_data.pop("password"))

    for key, value in update_data.items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)
    return user


# ────────────────────────────────
# Delete user
# ────────────────────────────────
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)
    # current_user: User = Depends(admin_required)
):
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()

    return {"message": "User deleted"}


# ────────────────────────────────
# Activate user
# ────────────────────────────────
@router.put("/users/{user_id}/activate", response_model=UserOut)
async def activate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)
    # current_user: User = Depends(admin_required)
):
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    await db.commit()
    await db.refresh(user)

    return user


# ────────────────────────────────
# Assign role to user
# ────────────────────────────────
@router.post("/users/{user_id}/roles/{role_id}")
async def assign_role_to_user(
    user_id: int,
    role_id: int,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)
    # current_user: User = Depends(admin_required)
):
    result_user = await db.execute(select(User).filter(User.id == user_id))
    user = result_user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result_role = await db.execute(select(Role).filter(Role.id == role_id))
    role = result_role.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role != user.role:
        user.role = role
        await db.commit()
        await db.refresh(user)

    return {"message": "Role assigned"}


# ────────────────────────────────
# Placeholder for sync users
# ────────────────────────────────
@router.post("/sync/users")
async def sync_users(
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)
    # current_user: User = Depends(admin_required)
):
    raise HTTPException(status_code=501, detail="Sync not implemented")
