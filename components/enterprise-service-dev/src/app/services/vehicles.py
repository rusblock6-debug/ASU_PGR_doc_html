"""Сервис для работы с транспортными средствами (Vehicle)."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Vehicle, VehicleModel
from app.schemas.vehicles import VehicleCreate, VehicleUpdate


class VehicleService:
    """Сервис для CRUD операций с транспортом."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        enterprise_id: int,
        vehicle_type: str | None = None,
        is_active: bool | None = None,
        page: int | None = 1,
        size: int | None = 20,
    ) -> dict[str, Any]:
        """Получить список транспорта с пагинацией или без неё.

        Если page и size не указаны (None), возвращает все записи без пагинации.
        Если указана только страница, размер берется по умолчанию 20.

        Returns:
            dict с ключами: total, page, size, items
        """
        query = select(Vehicle).where(Vehicle.enterprise_id == enterprise_id)

        if vehicle_type:
            query = query.where(Vehicle.vehicle_type == vehicle_type)

        if is_active is not None:
            query = query.where(Vehicle.is_active == is_active)

        # Если пагинация отключена (page и size не указаны)
        if page is None and size is None:
            query = query.options(selectinload(Vehicle.model))
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
        if page is None:
            page = 1
        if size is None:
            size = 20

        # Подсчёт
        count_query = select(func.count()).select_from(query.alias())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Пагинация + загрузка модели
        offset = (page - 1) * size
        query = query.options(selectinload(Vehicle.model)).offset(offset).limit(size)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return {
            "total": total,
            "page": page,
            "size": size,
            "items": items,
        }

    async def get_by_id(self, vehicle_id: int) -> Vehicle | None:
        """Получить транспорт по ID.

        Returns:
            Vehicle или None если не найден
        """
        result = await self.db.execute(
            select(Vehicle).options(selectinload(Vehicle.model)).where(Vehicle.id == vehicle_id),
        )
        return result.scalar_one_or_none()

    async def create(self, data: VehicleCreate) -> Vehicle:
        """Создать новый транспорт.

        Returns:
            Созданный Vehicle с загруженной моделью
        """
        vehicle = Vehicle(**data.model_dump())
        self.db.add(vehicle)
        await self.db.commit()

        # Перезагружаем с моделью
        result = await self.db.execute(
            select(Vehicle).options(selectinload(Vehicle.model)).where(Vehicle.id == vehicle.id),
        )
        return result.scalar_one()

    async def update(self, vehicle_id: int, data: VehicleUpdate) -> Vehicle | None:
        """Обновить транспорт.

        Returns:
            Обновлённый Vehicle или None если не найден
        """
        result = await self.db.execute(
            select(Vehicle).where(Vehicle.id == vehicle_id),
        )
        vehicle = result.scalar_one_or_none()

        if not vehicle:
            return None

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(vehicle, key, value)

        await self.db.commit()

        # Перезагружаем с моделью
        result = await self.db.execute(
            select(Vehicle).options(selectinload(Vehicle.model)).where(Vehicle.id == vehicle_id),
        )
        return result.scalar_one()

    async def delete(self, vehicle_id: int) -> bool:
        """Soft delete транспорта (is_active = False).

        Returns:
            True если удалён, False если не найден
        """
        result = await self.db.execute(
            select(Vehicle).where(Vehicle.id == vehicle_id),
        )
        vehicle = result.scalar_one_or_none()

        if not vehicle:
            return False

        vehicle.is_active = False
        await self.db.commit()
        return True

    async def copy(self, vehicle_id: int) -> Vehicle | None:
        """Скопировать существующий транспорт.

        Исключаются: id, created_at, updated_at, serial_number

        Returns:
            Новый Vehicle или None если исходный не найден
        """
        result = await self.db.execute(
            select(Vehicle).where(Vehicle.id == vehicle_id),
        )
        src = result.scalar_one_or_none()

        if not src:
            return None

        excluded_fields = {"id", "created_at", "updated_at", "serial_number"}
        copy_data = {
            col.name: getattr(src, col.name)
            for col in Vehicle.__table__.columns
            if col.name not in excluded_fields
        }

        copy_data["serial_number"] = None
        copy_data["name"] = f"{src.name} (копия)"

        new_vehicle = Vehicle(**copy_data)
        self.db.add(new_vehicle)
        await self.db.commit()

        # Перезагружаем с моделью
        result = await self.db.execute(
            select(Vehicle)
            .options(selectinload(Vehicle.model))
            .where(Vehicle.id == new_vehicle.id),
        )
        return result.scalar_one()

    async def get_model_max_speed(self, vehicle_id: int) -> float | None:
        """
        Получить максимальную скорость модели транспортного средства по vehicle_id.

        Args:
            vehicle_id: идентификатор транспортного средства

        Returns:
            Максимальная скорость (км/ч) или None, если ТС не найдено
            или у него не указана модель / модель не имеет max_speed.
        """
        result = await self.db.execute(
            select(VehicleModel.max_speed)
            .join(Vehicle, Vehicle.model_id == VehicleModel.id)
            .where(Vehicle.id == vehicle_id)
        )
        max_speed = result.scalar_one()
        return max_speed
