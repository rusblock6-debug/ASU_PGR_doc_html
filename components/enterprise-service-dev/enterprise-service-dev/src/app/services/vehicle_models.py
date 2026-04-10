"""Сервис для работы с моделями транспорта (VehicleModel)."""

from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Vehicle, VehicleModel
from app.schemas.vehicle_models import VehicleModelCreate, VehicleModelUpdate


class VehicleModelService:
    """Сервис для CRUD операций с моделями транспорта."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        page: int | None = 1,
        size: int | None = 20,
        consist: str | None = None,
    ) -> dict[str, Any]:
        """Получить список моделей транспорта с пагинацией или без неё.

        Если page и size не указаны (None), возвращает все записи без пагинации.

        Args:
            page: номер страницы (опционально)
            size: размер страницы (опционально)
            consist: фильтр по подстроке в названии (регистронезависимый)

        Returns:
            dict с ключами: total, page, size, items
        """
        query = select(VehicleModel)

        # Фильтр по подстроке в названии
        if consist:
            query = query.where(VehicleModel.name.ilike(f"%{consist}%"))

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
        # Подсчёт общего количества (с учётом фильтра)
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Пагинация
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

    async def get_by_id(self, model_id: int) -> VehicleModel | None:
        """Получить модель транспорта по ID.

        Returns:
            VehicleModel или None если не найдена
        """
        result = await self.db.execute(
            select(VehicleModel).where(VehicleModel.id == model_id),
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> VehicleModel | None:
        """Получить модель транспорта по имени.

        Returns:
            VehicleModel или None если не найдена
        """
        result = await self.db.execute(
            select(VehicleModel).where(VehicleModel.name == name),
        )
        return result.scalar_one_or_none()

    async def create(self, data: VehicleModelCreate) -> VehicleModel:
        """Создать новую модель транспорта.

        Returns:
            Созданная VehicleModel

        Raises:
            ValueError: если модель с таким именем уже существует
        """
        # Проверка уникальности имени
        existing = await self.get_by_name(data.name)
        if existing:
            raise ValueError(f"Модель с именем '{data.name}' уже существует")

        vehicle_model = VehicleModel(**data.model_dump())
        self.db.add(vehicle_model)
        await self.db.commit()
        await self.db.refresh(vehicle_model)
        return vehicle_model

    async def update(self, model_id: int, data: VehicleModelUpdate) -> VehicleModel | None:
        """Обновить модель транспорта.

        Returns:
            Обновлённая VehicleModel или None если не найдена

        Raises:
            ValueError: если новое имя уже занято другой моделью
        """
        vehicle_model = await self.get_by_id(model_id)
        if not vehicle_model:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Проверка уникальности имени при обновлении
        if "name" in update_data and update_data["name"] != vehicle_model.name:
            existing = await self.get_by_name(update_data["name"])
            if existing:
                raise ValueError(f"Модель с именем '{update_data['name']}' уже существует")

        for key, value in update_data.items():
            setattr(vehicle_model, key, value)

        await self.db.commit()
        await self.db.refresh(vehicle_model)
        return vehicle_model

    async def delete(self, model_id: int) -> bool:
        """Удалить модель транспорта.

        Перед удалением отвязывает все связанные Vehicle (устанавливает model_id = None).

        Returns:
            True если удалена, False если не найдена
        """
        vehicle_model = await self.get_by_id(model_id)
        if not vehicle_model:
            return False

        # Отвязываем все Vehicle от этой модели перед удалением
        count_query = select(func.count(Vehicle.id)).where(Vehicle.model_id == model_id)
        count_result = await self.db.execute(count_query)
        vehicles_count = count_result.scalar_one()

        if vehicles_count > 0:
            await self.db.execute(
                update(Vehicle).where(Vehicle.model_id == model_id).values(model_id=None),
            )

        await self.db.delete(vehicle_model)
        await self.db.commit()
        return True
