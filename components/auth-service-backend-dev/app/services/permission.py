from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.permission_model import Permission


async def get_permission_names(db: AsyncSession):
    """Получить список всех названий permission"""
    result = await db.execute(select(Permission.name))
    permission_names = result.scalars().all()
    return list(permission_names)


async def create_permissions(db: AsyncSession, permissions_list: list):
    """Создать permissions"""
    for perm_name in permissions_list:
        new_permission = Permission(name=perm_name)
        db.add(new_permission)

    await db.commit()
