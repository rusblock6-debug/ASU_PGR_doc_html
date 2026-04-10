"""Сервис для bulk операций с RouteTask.

Содержит бизнес-логику для массовых операций с route_tasks:
- Bulk upsert (создание + обновление множества за одну транзакцию)
- Bulk create (массовое создание)
- Bulk update (массовое обновление)
- MQTT публикация
"""

from typing import Any

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import coalesce

from app.api.schemas.tasks.route_tasks_bulk import (
    RouteTaskBulkUpsertItem,
    RouteTaskBulkUpsertRequest,
)
from app.database.models import RouteTask, ShiftTask
from app.enums import TripStatusRouteEnum
from app.services.tasks.route_task import RouteTaskService


class RouteTaskBulkService:
    """Сервис для bulk операций с RouteTask.

    Отвечает за:
    - Bulk upsert
    - Валидацию данных
    """

    @staticmethod
    async def bulk_upsert(
        data: RouteTaskBulkUpsertRequest,
        db: AsyncSession,
        shift_task_id: str | None = None,
    ) -> Any:
        """Bulk upsert route_tasks одним запросом INSERT ... ON CONFLICT DO UPDATE.

        Args:
            data: Список RouteTaskBulkUpsertItem
            db: Database session
            shift_task_id: если задан — подставляется всем строкам; иначе берётся из каждого item
        """
        try:
            items = data.items
            # 1. Валидация shift_task_id
            await RouteTaskBulkService.validate_shift_task_id(items, shift_task_id, db)

            # 2. Собираем запрос на upsert
            stmt = RouteTaskBulkService.get_stmt_for_bulk_upsert_route_tasks(items)

            # 3. Выполняем запрос
            result = await db.execute(stmt)
            await db.commit()
            logger.info(
                "[Completed] Bulk upsert route tasks",
            )

            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "[Failed] Bulk upsert route tasks",
                error=str(e),
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail=f"[Failed] Bulk upsert route tasks: {str(e)}",
            ) from e

    @staticmethod
    async def validate_shift_task_id(
        items: list[RouteTaskBulkUpsertItem],
        shift_task_id: str | None,
        db: AsyncSession,
    ) -> None:
        """Валидация shift_task_id в route_tasks."""
        shift_task_ids: set[str] = set()
        for item in items:
            if shift_task_id:
                item.shift_task_id = shift_task_id
            else:
                if item.shift_task_id is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid shift_task_id is None: {item.id}",
                    )
            # item.shift_task_id гарантированно не None после проверок выше
            shift_task_ids.add(str(item.shift_task_id))

        shift_tasks = await db.execute(
            select(ShiftTask.id).where(ShiftTask.id.in_(shift_task_ids)),
        )

        invalid_ids = shift_task_ids - {shift_task.id for shift_task in shift_tasks}
        if invalid_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Invalid shift_task_ids: {list(invalid_ids)}",
            )

        logger.info(
            "Valid shift_task_id in route_tasks",
        )
        return

    @staticmethod
    def get_stmt_for_bulk_upsert_route_tasks(
        items: list[RouteTaskBulkUpsertItem],
    ) -> Any:
        """Собираем запрос на bulk upsert route_tasks.

        При создании нового route_task (id = None):
        - Если статус SENT или EMPTY, меняется на DELIVERED
        """
        # Готовим список словарей
        values_list = [item.model_dump() for item in items]
        for row in values_list:
            if row.get("id") is None:
                row.pop("id", None)
                # При создании: если статус SENT или EMPTY, меняем на DELIVERED
                raw_status = row.get("status")
                row["status"] = RouteTaskService.normalize_status_for_creation(
                    raw_status if isinstance(raw_status, TripStatusRouteEnum) else TripStatusRouteEnum.EMPTY,
                )
        # создает SQL выражение для множественной вставки
        stmt = insert(RouteTask).values(values_list)

        # Создает динамический словарь для обновления полей при конфликте в UPSERT операции
        update_dict: dict[str, Any] = {}
        for column in RouteTask.__table__.columns:
            if column.name != "id":  # поле обычно не обновляется
                # Если значение NULL, оставляем старое значение
                update_dict[column.name] = coalesce(
                    getattr(stmt.excluded, column.name),
                    getattr(RouteTask, column.name),
                )
        # добавляет к INSERT запросу условие "при конфликте - обнови"
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_=update_dict,
        )
        return stmt
