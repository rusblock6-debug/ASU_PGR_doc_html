"""Сервис для работы с организационными категориями (OrganizationCategory)."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import OrganizationCategory
from app.schemas.statuses import OrganizationCategoryCreate, OrganizationCategoryUpdate


class OrganizationCategoryService:
    """Сервис для CRUD операций с организационными категориями."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        page: int | None = 1,
        size: int | None = 20,
    ) -> dict[str, Any]:
        """Получить список организационных категорий с пагинацией или без неё.

        Если page и size не указаны (None), возвращает все записи без пагинации.

        Returns:
            dict с ключами: total, page, size, items
        """
        query = select(OrganizationCategory)

        # Если пагинация отключена (page и size не указаны)
        if page is None and size is None:
            result = await self.db.execute(query)
            items = result.scalars().all()
            items_count = len(items)
            return {
                "total": items_count,
                "page": 1,
                "size": items_count if items_count > 0 else 1,
                "items": items,
            }

        # Пагинация включена
        count_query = select(func.count()).select_from(query.alias())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        page = page or 1
        size = size or 10
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return {
            "total": total,
            "page": page,
            "size": size,
            "items": items,
        }

    async def get_by_id(self, category_id: int) -> OrganizationCategory | None:
        """Получить категорию по ID.

        Returns:
            OrganizationCategory или None если не найдена
        """
        result = await self.db.execute(
            select(OrganizationCategory).where(OrganizationCategory.id == category_id),
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> OrganizationCategory | None:
        """Получить категорию по имени.

        Returns:
            OrganizationCategory или None если не найдена
        """
        result = await self.db.execute(
            select(OrganizationCategory).where(OrganizationCategory.name == name),
        )
        return result.scalar_one_or_none()

    async def create(self, data: OrganizationCategoryCreate) -> OrganizationCategory:
        """Создать новую категорию.

        Returns:
            Созданная OrganizationCategory
        """
        category = OrganizationCategory(**data.model_dump())
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def update(
        self,
        category_id: int,
        data: OrganizationCategoryUpdate,
    ) -> OrganizationCategory | None:
        """Обновить категорию.

        Returns:
            Обновлённая OrganizationCategory или None если не найдена
        """
        result = await self.db.execute(
            select(OrganizationCategory).where(OrganizationCategory.id == category_id),
        )
        category = result.scalar_one_or_none()

        if not category:
            return None

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(category, key, value)

        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def delete(self, category_id: int) -> bool:
        """Удалить категорию (hard delete).

        Returns:
            True если удалена, False если не найдена
        """
        result = await self.db.execute(
            select(OrganizationCategory).where(OrganizationCategory.id == category_id),
        )
        category = result.scalar_one_or_none()

        if not category:
            return False

        await self.db.delete(category)
        await self.db.commit()
        return True
