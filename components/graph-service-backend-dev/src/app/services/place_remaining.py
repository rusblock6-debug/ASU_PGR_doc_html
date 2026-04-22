"""Сервис для управления остатками на местах"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enum.places import PlaceTypeEnum, RemainingChangeTypeEnum
from app.models.database import Place

logger = logging.getLogger(__name__)


class PlaceRemainingService:
    """Сервис для управления остатками"""

    async def update_place_stock(
        self,
        db: AsyncSession,
        place_id: int,
        change_type: str,
        change_amount: float,
    ) -> bool:
        """Обновить остаток в place на основе изменения.

        Логика пересчета осталась в graph-service, но теперь работает инкрементально,
        так как история хранится в trip-service.

        Args:
            db: Сессия БД
            place_id: ID места
            change_type: Тип изменения ('loading', 'unloading', 'initial')
            change_amount: Signed delta (может быть отрицательной или положительной)

        Returns:
            True если успешно обновлено
        """
        try:
            # Проверяем, что место существует
            result = await db.execute(select(Place).where(Place.id == place_id))
            place = result.scalar_one_or_none()

            if not place:
                logger.error(f"Place {place_id} not found, cannot update stock")
                return False

            # Преобразуем change_type в enum
            try:
                change_type_enum = RemainingChangeTypeEnum(change_type)
            except ValueError:
                logger.error(f"Unknown change_type: {change_type}")
                return False

            # Применяем signed delta:
            # - loading обычно приходит с отрицательной дельтой
            # - unloading обычно приходит с положительной дельтой
            delta = float(change_amount)

            # Единая логика: load/unload/reload ведём через current_stock
            if place.type in (PlaceTypeEnum.load, PlaceTypeEnum.unload, PlaceTypeEnum.reload):
                current = getattr(place, "current_stock", None) or 0.0
                new_stock = current + delta
                place.current_stock = new_stock  # type: ignore[attr-defined]
            else:
                logger.warning(
                    f"Place {place_id} has type '{place.type}'"
                    " which does not support remaining tracking",
                )
                return False

            await db.commit()

            logger.info(
                f"Updated stock for place {place_id}: {current} -> {new_stock} "
                f"(type={change_type_enum.value}, delta={delta})",
            )

            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating place stock: {e}")
            raise


# Глобальный экземпляр сервиса
place_remaining_service = PlaceRemainingService()
