"""Сервис для bulk операций с ShiftTask.

Содержит бизнес-логику для массовых операций с shift_tasks:
- Bulk upsert (создание + обновление множества за одну транзакцией)
- Bulk create (массовое создание)
- Bulk update (массовое обновление)
"""

import copy
import json
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas.tasks.shift_tasks import ShiftTaskResponse
from app.api.schemas.tasks.shift_tasks_bulk import (
    ShiftTaskBulkUpsertRequest,
    ShiftTaskUpsertItem,
)
from app.core.config import settings
from app.core.redis_client import redis_client
from app.database.models import RouteTask, ShiftTask
from app.services.tasks.route_task_bulk import RouteTaskBulkService


class ShiftTaskBulkService:
    """Сервис для bulk операций с ShiftTask.

    Отвечает за:
    - Bulk upsert
    - Валидацию данных
    """

    @staticmethod
    async def bulk_upsert(
        data: ShiftTaskBulkUpsertRequest,
        db: AsyncSession,
    ) -> bool:
        """Bulk upsert shift_tasks."""
        try:
            items = data.items

            # 1. Удаление route_tasks которые не переданы
            await ShiftTaskBulkService.delete_route_tasks(items=items, db=db)

            # TODO нжуно для публикации в redis если у нас появится обстракция
            #  которая будет отслеживать изминения в бд и возьмет на себя отправку
            #  в redis то это нужно удалить
            changed_shift_tasks: list[tuple[str, str]] = []
            # =======================================================================

            # 2. Перебираем shift_tasks, выполняем single upsert shift task с flush(),
            # берем id от результата операции записываем его в shift_task_id,
            # запускаем валидация shift_task_id, собираем запрос на bulk upsert route task,
            # выполняем запрос на bulk upsert route task, выполняем commit()
            for shift_task in items:
                # 2.1. Single upsert shift task
                stmt = ShiftTaskBulkService.get_stmt_for_single_upsert_shift_task(item=shift_task)
                result_single_upsert_shift_task = await db.execute(stmt)
                await db.flush()

                # 2.2. Валидация shift_task_id
                shift_task_id = result_single_upsert_shift_task.scalar_one().id
                if shift_task.route_tasks is None:
                    raise RuntimeError("shift_task.route_tasks is not initialized")
                await RouteTaskBulkService.validate_shift_task_id(
                    shift_task.route_tasks,
                    shift_task_id,
                    db,
                )

                # 2.3. Bulk upsert route_tasks
                stmt = RouteTaskBulkService.get_stmt_for_bulk_upsert_route_tasks(
                    shift_task.route_tasks,
                )
                await db.execute(stmt)

                # 3. Для SSE/Redis: считаем, что без id — create, иначе update
                # TODO нжуно для публикации в redis если у нас появится обстракция
                #  которая будет отслеживать изминения в бд и возьмет на себя отправку
                #  в redis то это нужно удалить
                action = "create" if not shift_task.id else "update"
                changed_shift_tasks.append((shift_task_id, action))
                # ==================================================================
            # 4. Сохраняем в бд

            await db.commit()
            logger.info("[Completed] Bulk upsert shift tasks")

            # 5. Публикуем события в Redis для SSE (только в server режиме)
            # TODO нжуно для публикации в redis если у нас появится обстракция
            #  которая будет отслеживать изминения в бд и возьмет на себя отправку
            #  в redis то publish_shift_tasks_bulk_upsert_to_redis нужно удалить
            await ShiftTaskBulkService.publish_shift_tasks_bulk_upsert_to_redis(
                db=db,
                changed_shift_tasks=changed_shift_tasks,
            )
            # ===================================================================
            return True

        except Exception as e:
            logger.error("Bulk upsert failed", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=f"Bulk upsert failed: {str(e)}") from e

    @staticmethod
    async def publish_shift_tasks_bulk_upsert_to_redis(
        db: AsyncSession,
        changed_shift_tasks: list[tuple[str, str]],
        channel: str = "trip-service:shift_tasks:changes",
    ) -> None:
        """Публикует события об изменении shift_tasks в Redis (для SSE).

        Важно: вызывается после commit(), чтобы перечитать актуальные данные,
        включая связанные route_tasks.
        """
        if settings.service_mode != "server":
            return

        if redis_client.redis is None:
            logger.warning(
                "Redis client not connected, skipping Redis publish for bulk upsert",
            )
            return

        # Важно: перечитываем shift_task после commit с подгруженными route_tasks
        for shift_task_id, action in changed_shift_tasks:
            try:
                query = (
                    select(ShiftTask).options(selectinload(ShiftTask.route_tasks)).where(ShiftTask.id == shift_task_id)
                )
                result = await db.execute(query)
                shift_task_obj = result.scalar_one_or_none()
                if not shift_task_obj:
                    continue

                shift_task_data = ShiftTaskResponse.model_validate(shift_task_obj).model_dump(mode="json")
                redis_event = {
                    "event_type": "shift_task_changed",
                    "action": action,
                    "shift_task_id": str(shift_task_obj.id),
                    "vehicle_id": shift_task_obj.vehicle_id,
                    "shift_task": shift_task_data,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                await redis_client.redis.publish(
                    channel,
                    json.dumps(redis_event),
                )
            except Exception as e:
                logger.error(
                    "Failed to publish shift_task bulk upsert event to Redis",
                    shift_task_id=str(shift_task_id),
                    error=str(e),
                    exc_info=True,
                )

    @staticmethod
    async def delete_route_tasks(
        items: list[ShiftTaskUpsertItem],
        db: AsyncSession,
    ) -> None:
        """Удаление route_tasks, отсутствующих в переданном списке.

        Если есть route_tasks получаем список id route_tasks у каждой shift_task
        и удаляем все route_tasks которых нет в списке для этого shift_task.
        """
        for shift_task in items:
            # Пропускаем shift_task без ID
            if not shift_task.id:
                continue

            if shift_task.route_tasks is None:
                continue
            else:
                route_task_ids = {rt.id for rt in shift_task.route_tasks if hasattr(rt, "id") and rt.id is not None}

                # Формируем запрос на удаление
                if not route_task_ids:
                    # Если список пустой - удаляем ВСЕ route_tasks этого shift_task
                    stmt = delete(RouteTask).where(
                        RouteTask.shift_task_id == shift_task.id,
                    )
                else:
                    # Удаляем всё, кроме указанных ID
                    stmt = delete(RouteTask).where(
                        RouteTask.shift_task_id == shift_task.id,
                        ~RouteTask.id.in_(route_task_ids),
                    )
                await db.execute(stmt)
        return

    @staticmethod
    def get_stmt_for_single_upsert_shift_task(
        item: ShiftTaskUpsertItem,
    ) -> Any:
        """Single upsert для ShiftTask."""
        data_shift_task = copy.deepcopy(item.model_dump(exclude_unset=True))

        if data_shift_task.get("route_tasks") is not None:
            data_shift_task.pop("route_tasks", None)

        insert_stmt = insert(ShiftTask).values(data_shift_task)

        update_dict = {key: value for key, value in data_shift_task.items() if key != "id"}

        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["id"],
            set_=update_dict,
        ).returning(ShiftTask)

        return stmt
