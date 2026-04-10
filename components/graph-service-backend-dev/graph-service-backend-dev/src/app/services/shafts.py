"""Сервис для работы с шахтами (shafts)"""

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Shaft
from app.schemas.shafts import (
    ShaftBulkCreateRequest,
    ShaftBulkUpdateRequest,
    ShaftCreate,
    ShaftListResponse,
    ShaftResponse,
    ShaftUpdateSingle,
)

logger = logging.getLogger(__name__)


class ShaftService:
    """Сервис для работы с шахтами"""

    async def get_shafts(
        self,
        db: AsyncSession,
        page: int | None = None,
        size: int | None = None,
    ) -> ShaftListResponse:
        """Получить список всех шахт.

        Если параметры page и size не указаны — возвращает все записи.
        Если указан хотя бы один — применяется пагинация.
        """
        # Если пагинация отключена (page и size не указаны)
        if page is None and size is None:
            result = await db.execute(select(Shaft).order_by(Shaft.id))
            shafts = result.scalars().all()
            items_count = len(shafts)
            return ShaftListResponse(
                total=items_count,
                page=1,
                size=items_count if items_count > 0 else 1,
                items=[ShaftResponse.model_validate(shaft) for shaft in shafts],
            )
        else:
            # Пагинация включена — устанавливаем дефолтные значения
            page = page or 1
            size = size or 20

            total = await db.scalar(select(func.count()).select_from(Shaft))
            offset = (page - 1) * size
            result = await db.execute(
                select(Shaft).order_by(Shaft.id).offset(offset).limit(size),
            )
            shafts = result.scalars().all()

            return ShaftListResponse(
                total=total or 0,
                page=page,
                size=size,
                items=[ShaftResponse.model_validate(shaft) for shaft in shafts],
            )

    async def get_shaft(
        self,
        db: AsyncSession,
        shaft_id: int,
    ) -> ShaftResponse:
        """Получить шахту по ID"""
        result = await db.execute(select(Shaft).where(Shaft.id == shaft_id))
        shaft = result.scalar_one_or_none()

        if not shaft:
            raise ValueError("Shaft not found")

        return ShaftResponse.model_validate(shaft)

    async def create_shaft(
        self,
        db: AsyncSession,
        shaft_data: ShaftCreate,
    ) -> ShaftResponse:
        """Создать одну шахту"""
        existing = await db.scalar(select(Shaft).where(Shaft.name == shaft_data.name))
        if existing:
            raise ValueError(f"Шахта с названием '{shaft_data.name}' уже существует")

        shaft_dict = shaft_data.model_dump()
        # Если указан id, используем его (для синхронизации с сервером)
        if shaft_data.id is not None:
            shaft = Shaft(id=shaft_data.id, name=shaft_dict["name"])
        else:
            # Обычное создание с автоинкрементом
            shaft = Shaft(**{k: v for k, v in shaft_dict.items() if k != "id"})
        db.add(shaft)
        await db.commit()
        await db.refresh(shaft)

        return ShaftResponse.model_validate(shaft)

    async def create_shafts_bulk(
        self,
        db: AsyncSession,
        bulk_request: ShaftBulkCreateRequest,
    ) -> list[dict[str, Any]]:
        """Создать шахты (bulk операция)"""
        created = []

        for item in bulk_request.items:
            existing = await db.scalar(select(Shaft).where(Shaft.name == item.name))
            if existing:
                raise ValueError(f"Шахта с названием '{item.name}' уже существует")

            shaft = Shaft(**item.model_dump())
            db.add(shaft)
            created.append(shaft)

        await db.commit()
        for shaft in created:
            await db.refresh(shaft)

        return [ShaftResponse.model_validate(s).model_dump() for s in created]

    async def patch_shafts_bulk(
        self,
        db: AsyncSession,
        bulk_request: ShaftBulkUpdateRequest,
    ) -> list[dict[str, Any]]:
        """Bulk обновление шахт"""
        updated = []

        for item in bulk_request.items:
            result = await db.execute(select(Shaft).where(Shaft.id == item.id))
            shaft = result.scalar_one_or_none()

            if not shaft:
                raise ValueError(f"Шахта с ID {item.id} не найдена")

            if item.name != shaft.name:
                existing = await db.scalar(select(Shaft).where(Shaft.name == item.name))
                if existing:
                    raise ValueError(f"Шахта с названием '{item.name}' уже существует")

            shaft.name = item.name  # type: ignore[assignment]
            updated.append(shaft)

        await db.commit()
        for shaft in updated:
            await db.refresh(shaft)

        return [ShaftResponse.model_validate(s).model_dump() for s in updated]

    async def patch_shaft(
        self,
        db: AsyncSession,
        shaft_id: int,
        update_data: ShaftUpdateSingle,
    ) -> ShaftResponse:
        """Обновить одну шахту"""
        result = await db.execute(select(Shaft).where(Shaft.id == shaft_id))
        shaft = result.scalar_one_or_none()

        if not shaft:
            raise ValueError("Shaft not found")

        if update_data.name != shaft.name:
            existing = await db.scalar(select(Shaft).where(Shaft.name == update_data.name))
            if existing:
                raise ValueError(f"Шахта с названием '{update_data.name}' уже существует")

        shaft.name = update_data.name  # type: ignore[assignment]
        await db.commit()
        await db.refresh(shaft)

        return ShaftResponse.model_validate(shaft)

    async def delete_shaft(
        self,
        db: AsyncSession,
        shaft_id: int,
    ) -> dict[str, Any]:
        """Удалить шахту"""
        result = await db.execute(select(Shaft).where(Shaft.id == shaft_id))
        shaft = result.scalar_one_or_none()

        if not shaft:
            raise ValueError("Shaft not found")

        await db.delete(shaft)
        await db.commit()

        return {
            "status": "success",
            "message": "Shaft deleted successfully",
            "id": shaft_id,
        }


# Глобальный экземпляр сервиса
shaft_service = ShaftService()
