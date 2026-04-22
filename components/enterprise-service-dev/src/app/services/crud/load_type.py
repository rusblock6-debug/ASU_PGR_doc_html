"""CRUD сервис для видов грузов."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database.models import LoadType
from app.schemas.load_type import APICreateLoadType, APIUpdateLoadType

from .base import BaseCRUD


class LoadTypeCRUD(BaseCRUD[LoadType, APICreateLoadType, APIUpdateLoadType, int]):
    """CRUD операции для вида грузов."""

    def __init__(self, session: AsyncSession):
        """Инициализация LoadTypeCRUD."""
        super().__init__(LoadType, session)

    async def get_by_id(self, id: int) -> LoadType | None:
        """Получить вид груза по ID."""
        return await self.session.scalar(
            select(LoadType)
            .options(
                joinedload(LoadType.category),
            )
            .where(LoadType.id == id),
        )

    async def get_all(self, page: int | None = None, size: int | None = None) -> dict[str, Any]:
        """Получить список видов грузов с пагинацией или без неё.

        Если page и size не указаны (None), возвращает все записи без пагинации.

        Args:
            page: номер страницы (опционально)
            size: размер страницы (опционально)

        Returns:
            dict с ключами: total, page, size, items
        """
        query = select(LoadType).options(joinedload(LoadType.category))

        # Если пагинация отключена (page и size не указаны)
        if page is None and size is None:
            result = await self.session.execute(query)
            items = result.scalars().all()
            items_count = len(items)
            return {
                "total": items_count,
                "page": 1,
                "size": items_count if items_count > 0 else 1,
                "items": items,
            }

        # Пагинация включена
        # Подсчёт общего количества
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # Пагинация
        page = page or 1
        size = size or 10
        offset = (page - 1) * size
        query = query.offset(offset).limit(size).order_by(LoadType.id.desc())

        result = await self.session.execute(query)
        items = result.scalars().all()

        return {
            "total": total,
            "page": page,
            "size": size,
            "items": items,
        }
