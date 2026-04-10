"""Сервис для работы с метками (tags)"""

import logging
from datetime import datetime
from typing import Any

from geoalchemy2.functions import ST_Point
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.database import Horizon, Tag
from app.schemas.tags import (
    APITagCreateModel,
    APITagResponseModel,
)
from app.utils.validation import (
    handle_validation_errors,
    safe_float_conversion,
    validate_tag_data,
)

logger = logging.getLogger(__name__)


# TODO возможно можно дропать
class TagService:
    """Сервис для работы с метками"""

    async def get_tag_by_id(self, db: AsyncSession, tag_id: int) -> APITagResponseModel:
        result = await db.execute(
            select(Tag).where(Tag.id == tag_id).options(joinedload(Tag.horizon)),  # type: ignore[attr-defined]
        )
        tag = result.scalar_one_or_none()
        if not tag:
            raise ValueError(f"Tag {tag_id} not found")
        return APITagResponseModel.model_validate(tag)

    async def create_tag(
        self,
        db: AsyncSession,
        tag_data: APITagCreateModel,
    ) -> APITagResponseModel:
        """Создать новую метку"""
        horizon = await db.scalar(select(Horizon).where(Horizon.id == tag_data.horizon_id))  # type: ignore[attr-defined]
        if not horizon:
            raise ValueError(f"Horizon {tag_data.horizon_id} not found")  # type: ignore[attr-defined]

        tag_dict = tag_data.model_dump()
        # Если указан id, используем его (для синхронизации с сервером)
        # if tag_data.id is not None:
        #     tag = Tag(
        #         id=tag_data.id,
        #         horizon_id=tag_dict['horizon_id'],
        #         x=tag_dict['x'],
        #         y=tag_dict['y'],
        #         radius=tag_dict.get('radius', 25.0),
        #         name=tag_dict['name'],
        #         point_type=tag_dict['point_type'],
        #         point_id=tag_dict.get('point_id'),
        #         beacon_id=tag_dict.get('beacon_id'),
        #         beacon_mac=tag_dict.get('beacon_mac'),
        #         beacon_place=tag_dict.get('beacon_place'),
        #         battery_level=tag_dict.get('battery_level'),
        #         battery_updated_at=tag_dict.get('battery_updated_at')
        #     )
        # else:
        #     # Обычное создание с автоинкрементом
        #     tag = Tag(**{k: v for k, v in tag_dict.items() if k != 'id'})
        # tag.geometry = ST_Point(tag_data.x, tag_data.y, srid=4326)
        # tag.zone_geometry = func.ST_Buffer(tag.geometry, tag.radius)

        tag = Tag(**tag_dict)
        db.add(tag)

        try:
            await db.commit()
        except IntegrityError as e:
            await db.rollback()
            if "point_id" in str(e):
                raise ValueError(f"Метка с point_id '{tag_data.point_id}' уже существует") from e  # type: ignore[attr-defined]
            raise

        result = await db.execute(
            select(Tag).where(Tag.id == tag.id).options(joinedload(Tag.horizon)),  # type: ignore[attr-defined]
        )
        tag = result.scalar_one()
        return APITagResponseModel.model_validate(tag)

    async def update_tag(
        self,
        db: AsyncSession,
        tag_id: int,
        update_data: dict[str, Any],
    ) -> APITagResponseModel:
        """Обновить метку"""
        result = await db.execute(select(Tag).where(Tag.id == tag_id))
        tag = result.scalar_one_or_none()

        if not tag:
            raise ValueError(f"Tag {tag_id} not found")

        is_valid, errors = validate_tag_data(update_data)
        if not is_valid:
            raise ValueError(handle_validation_errors(errors, "Обновление метки"))

        for field in [
            "name",
            "point_type",
            "point_id",
            "radius",
            "beacon_id",
            "beacon_mac",
            "beacon_place",
        ]:
            if field in update_data:
                setattr(tag, field, update_data[field])

        if "x" in update_data or "y" in update_data:
            tag.x = safe_float_conversion(update_data.get("x", tag.x), tag.x)  # type: ignore[attr-defined]
            tag.y = safe_float_conversion(update_data.get("y", tag.y), tag.y)  # type: ignore[attr-defined]

            tag.geometry = ST_Point(tag.x, tag.y, srid=4326)  # type: ignore[attr-defined]
            tag.zone_geometry = func.ST_Buffer(tag.geometry, tag.radius)  # type: ignore[attr-defined]

        tag.updated_at = datetime.utcnow()

        try:
            await db.commit()
        except IntegrityError as e:
            await db.rollback()
            if "point_id" in str(e):
                raise ValueError(
                    f"Метка с point_id '{update_data.get('point_id')}' уже существует",
                ) from e
            raise

        result = await db.execute(
            select(Tag).where(Tag.id == tag_id).options(joinedload(Tag.horizon)),  # type: ignore[attr-defined]
        )
        tag = result.scalar_one()
        return APITagResponseModel.model_validate(tag)

    async def delete_tag(
        self,
        db: AsyncSession,
        tag_id: int,
    ) -> dict[str, str]:
        """Удалить метку"""
        result = await db.execute(select(Tag).where(Tag.id == tag_id))
        tag = result.scalar_one_or_none()

        if not tag:
            raise ValueError(f"Tag {tag_id} not found")

        await db.delete(tag)
        await db.commit()

        return {"status": "success", "message": "Tag deleted successfully"}


# Глобальный экземпляр сервиса
tag_service = TagService()
