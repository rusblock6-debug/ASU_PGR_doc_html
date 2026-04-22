"""Сервис для работы со статусами (Status)."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Status
from app.schemas.statuses import StatusCreate, StatusUpdate, transliterate


class StatusService:
    """Сервис для CRUD операций со статусами."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _generate_system_name(self, display_name: str) -> str:
        """Генерирует уникальный system_name из display_name.

        Returns:
            Уникальный system_name
        """
        base_name = transliterate(display_name)

        # Если базовое имя пустое, используем fallback
        if not base_name:
            base_name = "status"

        # Проверяем уникальность
        system_name = base_name
        counter = 1

        while True:
            result = await self.db.execute(
                select(Status).where(Status.system_name == system_name),
            )
            existing = result.scalar_one_or_none()

            if existing is None:
                break

            system_name = f"{base_name}_{counter}"
            counter += 1

        return system_name

    async def get_list(
        self,
        page: int | None = 1,
        size: int | None = 20,
    ) -> dict[str, Any]:
        """Получить список статусов с пагинацией или без неё.

        Если page и size не указаны (None), возвращает все записи без пагинации.

        Returns:
            dict с ключами: total, page, size, items
        """
        query = select(Status)

        # Если пагинация отключена (page и size не указаны)
        if page is None and size is None:
            query = query.options(selectinload(Status.organization_category_rel))
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
        query = (
            query.options(
                selectinload(Status.organization_category_rel),
            )
            .offset(offset)
            .limit(size)
        )

        result = await self.db.execute(query)
        items = result.scalars().all()

        return {
            "total": total,
            "page": page,
            "size": size,
            "items": items,
        }

    async def get_by_id(self, status_id: int) -> Status | None:
        """Получить статус по ID.

        Returns:
            Status или None если не найден
        """
        result = await self.db.execute(
            select(Status)
            .options(selectinload(Status.organization_category_rel))
            .where(Status.id == status_id),
        )
        return result.scalar_one_or_none()

    async def get_by_system_name(self, system_name: str) -> Status | None:
        """Получить статус по system_name.

        Returns:
            Status или None если не найден
        """
        result = await self.db.execute(
            select(Status)
            .options(selectinload(Status.organization_category_rel))
            .where(Status.system_name == system_name),
        )
        return result.scalar_one_or_none()

    async def create(self, data: StatusCreate) -> Status:
        """Создать новый статус.

        Для system_status = false автоматически генерирует
        system_name из display_name с транслитерацией.
        Для system_status = true использует system_name как есть
        (если указан), иначе оставляет null.

        Returns:
            Созданный Status с загруженной organization_category
        """
        status_data = data.model_dump()

        # Генерируем system_name в зависимости от system_status и наличия system_name
        if data.system_name:
            # Если system_name явно указан, используем его
            system_name = data.system_name
        else:
            if data.system_status:
                # Для системных статусов оставляем system_name как null
                system_name = None
            else:
                # Для пользовательских статусов используем транслитерацию
                system_name = await self._generate_system_name(data.display_name)

        status_data["system_name"] = system_name

        status_obj = Status(**status_data)
        self.db.add(status_obj)
        await self.db.commit()

        # Перезагружаем с organization_category
        result = await self.db.execute(
            select(Status)
            .options(selectinload(Status.organization_category_rel))
            .where(Status.id == status_obj.id),
        )
        return result.scalar_one()

    async def update(self, status_id: int, data: StatusUpdate) -> Status | None:
        """Обновить статус.

        Если обновляется display_name и system_status = false,
        автоматически генерирует новый system_name с транслитерацией.
        Если system_status = true, system_name остается неизменным
        (если не указан явно).

        Returns:
            Обновлённый Status или None если не найден
        """
        result = await self.db.execute(
            select(Status).where(Status.id == status_id),
        )
        status_obj = result.scalar_one_or_none()

        if not status_obj:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Определяем system_status (старый или новый)
        current_system_status = update_data.get("system_status", status_obj.system_status)

        # Если обновляется display_name, генерируем новый system_name в зависимости от system_status
        if "display_name" in update_data and "system_name" not in update_data:
            # system_name не указан явно, генерируем автоматически
            if current_system_status:
                # Для системных статусов оставляем system_name без изменений
                pass  # не трогаем system_name
            else:
                # Для пользовательских статусов используем транслитерацию
                new_system_name = await self._generate_system_name(update_data["display_name"])
                update_data["system_name"] = new_system_name

        for key, value in update_data.items():
            setattr(status_obj, key, value)

        await self.db.commit()

        # Перезагружаем с organization_category
        result = await self.db.execute(
            select(Status)
            .options(selectinload(Status.organization_category_rel))
            .where(Status.id == status_id),
        )
        return result.scalar_one()

    async def delete(self, status_id: int) -> bool:
        """Удалить статус (hard delete).

        Returns:
            True если удалён, False если не найден
        """
        result = await self.db.execute(
            select(Status).where(Status.id == status_id),
        )
        status_obj = result.scalar_one_or_none()

        if not status_obj:
            return False

        await self.db.delete(status_obj)
        await self.db.commit()
        return True
