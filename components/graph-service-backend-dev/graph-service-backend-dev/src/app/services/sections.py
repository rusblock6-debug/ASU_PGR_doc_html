"""Сервис для работы с участками (sections)"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.database import Horizon, Section
from app.schemas.sections import (
    SectionCreate,
    SectionListBulkCreate,
    SectionListBulkUpdate,
    SectionListResponse,
    SectionResponse,
    SectionUpdate,
)
from config.settings import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)


class SectionService:
    """Сервис для работы с участками"""

    async def get_sections(
        self,
        db: AsyncSession,
        page: int | None = None,
        size: int | None = None,
    ) -> SectionListResponse:
        """Получить список всех участков.

        Если параметры page и size не указаны — возвращает все записи.
        Если указан хотя бы один — применяется пагинация.
        """
        # Если пагинация отключена (page и size не указаны)
        if page is None and size is None:
            result = await db.execute(
                select(Section).options(selectinload(Section.horizons)).order_by(Section.id),
            )
            sections = result.scalars().all()
            items_count = len(sections)
            return SectionListResponse(
                total=items_count,
                page=1,
                size=items_count if items_count > 0 else 1,
                items=[SectionResponse.model_validate(s) for s in sections],
            )
        else:
            # Пагинация включена — устанавливаем дефолтные значения
            page = page or 1
            size = size or 20

            total = await db.scalar(select(func.count()).select_from(Section))
            offset = (page - 1) * size
            result = await db.execute(
                select(Section)
                .options(selectinload(Section.horizons))
                .order_by(Section.id)
                .offset(offset)
                .limit(size),
            )
            sections = result.scalars().all()

            return SectionListResponse(
                total=total or 0,
                page=page,
                size=size,
                items=[SectionResponse.model_validate(s) for s in sections],
            )

    async def get_section(
        self,
        db: AsyncSession,
        section_id: int,
    ) -> SectionResponse:
        """Получить участок по ID"""
        result = await db.execute(
            select(Section).options(selectinload(Section.horizons)).where(Section.id == section_id),
        )
        section = result.scalar_one_or_none()

        if not section:
            raise ValueError(f"Section {section_id} not found")

        return SectionResponse.model_validate(section)

    async def create_section(
        self,
        db: AsyncSession,
        section_data: SectionCreate,
    ) -> SectionResponse:
        """Создать новый участок"""
        # Проверяем уникальность имени
        existing = await db.scalar(select(Section).where(Section.name == section_data.name))
        if existing:
            raise ValueError(f"Участок с названием '{section_data.name}' уже существует")

        section_dict = section_data.model_dump(exclude={"horizons", "id"})

        # Если указан id, используем его (для синхронизации с сервером)
        if section_data.id is not None:
            section = Section(
                id=section_data.id,
                name=section_dict["name"],
                is_contractor_organization=section_dict.get("is_contractor_organization"),
            )
        else:
            # Обычное создание с автоинкрементом
            section = Section(**section_dict)

        db.add(section)
        await db.flush()

        # Привязываем горизонты, если они указаны
        if section_data.horizons:
            horizons_result = await db.execute(
                select(Horizon).where(Horizon.id.in_(section_data.horizons)),
            )
            horizons = horizons_result.scalars().all()
            if len(horizons) != len(section_data.horizons):
                found_ids = {h.id for h in horizons}
                missing = [hid for hid in section_data.horizons if hid not in found_ids]
                raise ValueError(f"Горизонты не найдены: {missing}")

            # Загружаем section с предзагруженными связями, чтобы избежать lazy loading
            result = await db.execute(
                select(Section)
                .options(selectinload(Section.horizons))
                .where(Section.id == section.id),
            )
            section = result.scalar_one()
            section.horizons = list(horizons)

        await db.commit()
        await db.refresh(section, ["horizons"])

        if settings.is_server_mode:
            from app.services.event_publisher import event_publisher

            await event_publisher.publish_entity_changed("section", str(section.id), "create")

        return SectionResponse.model_validate(section)

    async def create_sections_bulk(
        self,
        db: AsyncSession,
        bulk_request: SectionListBulkCreate,
    ) -> list[dict[str, Any]]:
        """Создать участки (bulk операция)"""
        created = []

        for item in bulk_request.items:
            # Проверяем уникальность имени
            existing = await db.scalar(select(Section).where(Section.name == item.name))
            if existing:
                raise ValueError(f"Участок с названием '{item.name}' уже существует")

            section_dict = item.model_dump(exclude={"horizons", "id"})

            # Если указан id, используем его
            if item.id is not None:
                section = Section(
                    id=item.id,
                    name=section_dict["name"],
                    is_contractor_organization=section_dict.get("is_contractor_organization"),
                )
            else:
                section = Section(**section_dict)

            db.add(section)
            await db.flush()

            # Привязываем горизонты, если они указаны
            if item.horizons:
                horizons_result = await db.execute(
                    select(Horizon).where(Horizon.id.in_(item.horizons)),
                )
                horizons = horizons_result.scalars().all()
                if len(horizons) != len(item.horizons):
                    found_ids = {h.id for h in horizons}
                    missing = [hid for hid in item.horizons if hid not in found_ids]
                    raise ValueError(f"Горизонты не найдены для участка '{item.name}': {missing}")

                # Загружаем section с предзагруженными связями, чтобы избежать lazy loading
                result = await db.execute(
                    select(Section)
                    .options(selectinload(Section.horizons))
                    .where(Section.id == section.id),
                )
                section = result.scalar_one()
                section.horizons = list(horizons)

            created.append(section)

        await db.commit()
        for section in created:
            await db.refresh(section, ["horizons"])

        if settings.is_server_mode:
            from app.services.event_publisher import event_publisher

            for section in created:
                await event_publisher.publish_entity_changed("section", str(section.id), "create")

        return [SectionResponse.model_validate(s).model_dump() for s in created]

    async def patch_section(
        self,
        db: AsyncSession,
        section_id: int,
        update_data: SectionUpdate,
    ) -> SectionResponse:
        """Обновить участок"""
        # Загружаем участок с предзагруженными связями
        result = await db.execute(
            select(Section).options(selectinload(Section.horizons)).where(Section.id == section_id),
        )
        section = result.scalar_one_or_none()

        if not section:
            raise ValueError(f"Section {section_id} not found")

        # Обновляем имя, если указано
        if update_data.name is not None:
            # Проверяем уникальность нового имени
            if update_data.name != section.name:
                existing = await db.scalar(
                    select(Section).where(Section.name == update_data.name),
                )
                if existing:
                    raise ValueError(f"Участок с названием '{update_data.name}' уже существует")
            section.name = update_data.name  # type: ignore[assignment]

        # Обновляем флаг контрактной организации
        if update_data.is_contractor_organization is not None:
            section.is_contractor_organization = update_data.is_contractor_organization  # type: ignore[assignment]

        # Обновляем горизонты, если указаны
        if update_data.horizons is not None:
            if update_data.horizons:
                horizons_result = await db.execute(
                    select(Horizon).where(Horizon.id.in_(update_data.horizons)),
                )
                horizons = horizons_result.scalars().all()
                if len(horizons) != len(update_data.horizons):
                    found_ids = {h.id for h in horizons}
                    missing = [hid for hid in update_data.horizons if hid not in found_ids]
                    raise ValueError(f"Горизонты не найдены: {missing}")
                section.horizons = list(horizons)
            else:
                # Пустой список означает удаление всех связей
                section.horizons = []

        section.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(section, ["horizons"])

        if settings.is_server_mode:
            from app.services.event_publisher import event_publisher

            await event_publisher.publish_entity_changed("section", str(section_id), "update")

        return SectionResponse.model_validate(section)

    async def patch_sections_bulk(
        self,
        db: AsyncSession,
        bulk_request: SectionListBulkUpdate,
    ) -> list[dict[str, Any]]:
        """Bulk обновление участков"""
        updated = []

        for item in bulk_request.items:
            result = await db.execute(
                select(Section)
                .options(selectinload(Section.horizons))
                .where(Section.id == item.id),
            )
            section = result.scalar_one_or_none()

            if not section:
                raise ValueError(f"Участок с ID {item.id} не найден")

            # Обновляем имя, если указано
            if item.name is not None:
                if item.name != section.name:
                    existing = await db.scalar(
                        select(Section).where(Section.name == item.name),
                    )
                    if existing:
                        raise ValueError(f"Участок с названием '{item.name}' уже существует")
                section.name = item.name  # type: ignore[assignment]

            # Обновляем флаг контрактной организации
            if item.is_contractor_organization is not None:
                section.is_contractor_organization = item.is_contractor_organization  # type: ignore[assignment]

            # Обновляем горизонты, если указаны
            if item.horizons is not None:
                if item.horizons:
                    horizons_result = await db.execute(
                        select(Horizon).where(Horizon.id.in_(item.horizons)),
                    )
                    horizons = horizons_result.scalars().all()
                    if len(horizons) != len(item.horizons):
                        found_ids = {h.id for h in horizons}
                        missing = [hid for hid in item.horizons if hid not in found_ids]
                        raise ValueError(
                            f"Горизонты не найдены для участка ID {item.id}: {missing}",
                        )
                    section.horizons = list(horizons)
                else:
                    section.horizons = []

            section.updated_at = datetime.utcnow()
            updated.append(section)

        await db.commit()
        for section in updated:
            await db.refresh(section, ["horizons"])

        if settings.is_server_mode:
            from app.services.event_publisher import event_publisher

            for section in updated:
                await event_publisher.publish_entity_changed("section", str(section.id), "update")

        return [SectionResponse.model_validate(s).model_dump() for s in updated]

    async def delete_section(
        self,
        db: AsyncSession,
        section_id: int,
    ) -> dict[str, Any]:
        """Удалить участок"""
        result = await db.execute(select(Section).where(Section.id == section_id))
        section = result.scalar_one_or_none()

        if not section:
            raise ValueError(f"Section {section_id} not found")

        section_name = section.name
        await db.delete(section)
        await db.commit()

        if settings.is_server_mode:
            from app.services.event_publisher import event_publisher

            await event_publisher.publish_entity_changed("section", str(section_id), "delete")

        return {
            "status": "success",
            "message": "Section deleted successfully",
            "id": section_id,
            "name": section_name,
        }


# Глобальный экземпляр сервиса
section_service = SectionService()
