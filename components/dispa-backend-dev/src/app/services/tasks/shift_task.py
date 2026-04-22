"""Сервис для работы с ShiftTask.

Содержит бизнес-логику создания, preview и управления задачами с:
- Relationship для автосериализации
- Diff логикой для route_tasks
"""

from datetime import date
from typing import Any

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.tasks.route_tasks_bulk import (
    RouteTaskBulkUpsertItem,
    RouteTaskBulkUpsertRequest,
)
from app.api.schemas.tasks.shift_tasks import (
    ShiftTaskCreate,
    ShiftTaskResponse,
    ShiftTaskUpdate,
)
from app.api.schemas.tasks.shift_tasks_bulk import ShiftTaskBulkUpsertRequest, ShiftTaskUpsertItem
from app.database.base import generate_uuid
from app.database.models import RouteTask, ShiftTask
from app.enums import ShiftTaskStatusEnum, TripStatusRouteEnum
from app.services.enterprise_client import enterprise_client
from app.services.tasks.route_task_bulk import RouteTaskBulkService
from app.services.tasks.shift_task_bulk import ShiftTaskBulkService

CurrentShiftInfo = dict[str, Any]


class ShiftTaskService:
    """Сервис для бизнес-логики ShiftTask.

    Отвечает за:
    - Получение задач из предыдущей смены
    - Обновление с diff логикой для route_tasks
    - Валидацию и обработку данных
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_shift_changed(
        self,
        regimes_shift_data: dict[int, CurrentShiftInfo],
    ) -> dict[int, CurrentShiftInfo]:
        """Определить режимы работы, где смена действительно изменилась.

        Важно:
        - На cold start только инициализирует кеш `regimes_shift_data`
        - Возвращает только изменившиеся режимы (`changed_regimes`)
        """
        work_regimes = await enterprise_client.get_active_work_regimes()
        if not work_regimes:
            logger.warning("No active work regimes found in enterprise-service")
            return {}

        changed_regimes: dict[int, CurrentShiftInfo] = {}
        for work_regime in work_regimes:
            work_regime_id = work_regime["id"]
            current_shift = await enterprise_client.get_current_shift_info(work_regime_id)
            if current_shift is None:
                logger.warning(
                    "Current shift info was not found",
                    work_regime_id=work_regime_id,
                )
                continue

            cached_shift = regimes_shift_data.get(work_regime_id)
            if cached_shift is None:
                regimes_shift_data[work_regime_id] = current_shift
                continue

            if cached_shift["shift_num"] != current_shift["shift_num"]:
                changed_regimes[work_regime_id] = current_shift

        return changed_regimes

    async def preview_from_previous_shift(
        self,
        work_regime_id: int,
        target_date: date,
        target_shift_num: int,
    ) -> list[ShiftTaskResponse]:
        """Получение задач и маршрутов из предыдущей смены с адаптированными датами.

        Логика:
        - Получает ВСЕ активные WorkRegime из enterprise-service через API
        - Для каждого work_regime_id получает предыдущую смену через API
        - Находит все ShiftTask из предыдущей смены для всех режимов работы
        - Исключает задания, где есть RouteTask со статусом COMPLETED,
        - Сериализует ShiftTask и RouteTask с адаптированными датами

        Args:
            work_regime_id: ID режима работы
            target_date: Дата, на которую адаптировать (YYYY-MM-DD)
            target_shift_num: Номер смены, на которую адаптировать
            db: Database session

        Returns:
            Список заданий из предыдущей смены с адаптированными датами (ShiftTaskResponse)

        Raises:
            HTTPException(503): Не удалось подключиться к enterprise-service
        """
        # 1. Получить предыдущую смену (дату и номер смены)
        # Запрос к ентерпрайзу за поиском предыдущей смены
        prev_shift = await enterprise_client.get_prev_shift(
            work_regime_id=work_regime_id,
            current_shift_number=target_shift_num,
            current_date=target_date,
        )
        if prev_shift is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Previous shift not found",
            ) from None

        # Извлечь дату и номер предыдущей смены из запроса к ентерпрайз сервису
        prev_date = date.fromisoformat(prev_shift["date"])
        prev_num = prev_shift["shift_number"]

        # 3. Найти все ShiftTask из предыдущей смены для этого work_regime_id
        preview_tasks: list[ShiftTaskResponse] = []
        query = select(ShiftTask).where(
            (ShiftTask.work_regime_id == work_regime_id)
            & (ShiftTask.shift_date == prev_date.isoformat())
            & (ShiftTask.shift_num == prev_num),
        )
        result = await self.session.execute(query)
        prev_shift_tasks = result.scalars().all()

        if not prev_shift_tasks:
            logger.debug(
                "No shift tasks found in previous shift",
                work_regime_id=work_regime_id,
                prev_shift_date=prev_date.isoformat(),
                prev_shift_num=prev_num,
            )

        # 4. Копировать каждое задание
        for prev_task in prev_shift_tasks:
            # 5. Сериализовать задание из предыдущей смены
            # route_tasks загружаются автоматически через relationship
            serialized = ShiftTaskResponse.model_validate(prev_task).model_dump()
            # Исключаем только route_tasks со статусом COMPLETED, не всё задание целиком.
            serialized["route_tasks"] = [
                rt for rt in serialized.get("route_tasks", []) if rt.get("status") != TripStatusRouteEnum.COMPLETED
            ]

            # 6. Адаптировать даты для preview
            serialized["shift_date"] = target_date.isoformat()
            serialized["shift_num"] = target_shift_num

            # 7. Создать ShiftTaskResponse с адаптированными данными
            preview_task = ShiftTaskResponse(**serialized)
            preview_tasks.append(preview_task)

            logger.debug(
                f"Preview task {prev_task.id} adapted",
                work_regime_id=work_regime_id,
                vehicle_id=prev_task.vehicle_id,
                prev_shift_date=prev_date.isoformat(),
                prev_shift_num=prev_num,
                target_date=target_date.isoformat(),
                target_shift_num=target_shift_num,
            )

        logger.info(
            f"Preview {len(preview_tasks)} tasks from previous shift",
            target_date=target_date.isoformat(),
            target_shift_num=target_shift_num,
        )

        return preview_tasks

    async def copy_from_previous_shift(
        self,
        regimes_shift_data: dict[int, CurrentShiftInfo],
        changed_regimes: dict[int, CurrentShiftInfo],
    ) -> dict[int, CurrentShiftInfo]:
        """Копировать задания из предыдущей смены при переходе на новую смену.

        Логика:
        - Ожидает, что проверка "смена изменилась" уже выполнена в scheduler
        - Обрабатывает только переданные `changed_regimes`
        - Для каждого режима работы берет задания из предыдущей смены,
          адаптирует их под новую смену и создает через bulk upsert
        - Если в предыдущей смене нет заданий, пропускает режим работы

        Args:
            regimes_shift_data: Кеш текущих смен по `work_regime_id`
            changed_regimes: Режимы работы, где смена уже определена как изменившаяся

        Returns:
            Обновленный кеш текущих смен по режимам работы
        """
        for work_regime_id, current_shift in changed_regimes.items():
            cached_shift = regimes_shift_data.get(work_regime_id)
            if cached_shift is None:
                continue

            logger.info(
                "Shift num was changed",
                before_shift_num=cached_shift["shift_num"],
                now_shift_num=current_shift["shift_num"],
            )
            try:
                previous_shift_data = await self.preview_from_previous_shift(
                    work_regime_id,
                    date.fromisoformat(current_shift["shift_date"]),
                    current_shift["shift_num"],
                )
                if not previous_shift_data:
                    logger.info(
                        "No shift tasks to copy from previous shift",
                        work_regime_id=work_regime_id,
                        shift_date=current_shift["shift_date"],
                        shift_num=current_shift["shift_num"],
                    )
                    continue
                request = ShiftTaskBulkUpsertRequest(
                    items=[
                        ShiftTaskUpsertItem.model_validate(
                            {
                                **shift_task.model_dump(exclude={"id", "route_tasks"}),
                                "route_tasks": [
                                    {
                                        **route_task.model_dump(exclude={"id", "shift_task_id"}),
                                    }
                                    for route_task in shift_task.route_tasks
                                ],
                            },
                        )
                        for shift_task in previous_shift_data
                    ],
                )
                await ShiftTaskBulkService.bulk_upsert(
                    data=request,
                    db=self.session,
                )
                logger.info("Переключение смены прошло успешно", shift_num=current_shift["shift_num"])
            except Exception as exc:
                logger.exception("Ошибка переключения смены", exc_info=exc)
        return regimes_shift_data

    async def complete_previous_shift_route_tasks(
        self,
        regimes_shift_data: dict[int, CurrentShiftInfo],
        changed_regimes: dict[int, CurrentShiftInfo],
    ) -> int:
        """Перевести route_tasks предыдущих смен в COMPLETED.

        Для каждого режима из `changed_regimes` берется предыдущая смена из кеша
        `regimes_shift_data` (до обновления на новую смену). Текущая смена не трогается.

        Returns:
            Количество измененных route_tasks.
        """
        updated_total = 0
        for work_regime_id in changed_regimes:
            cached_shift = regimes_shift_data.get(work_regime_id)
            if cached_shift is None:
                continue

            prev_shift_num = cached_shift.get("shift_num")
            prev_shift_date = cached_shift.get("shift_date")

            stmt = (
                update(RouteTask)
                .where(
                    RouteTask.shift_task_id.in_(
                        select(ShiftTask.id).where(
                            (ShiftTask.work_regime_id == work_regime_id)
                            & (ShiftTask.shift_num == prev_shift_num)
                            & (ShiftTask.shift_date == prev_shift_date),
                        ),
                    ),
                )
                .values(status=TripStatusRouteEnum.COMPLETED)
            )
            res = await self.session.execute(stmt)
            updated_total += res.rowcount  # type: ignore[attr-defined, unused-ignore]

        if updated_total > 0:
            await self.session.commit()

        logger.info(
            "Previous shift route_tasks completed",
            updated=updated_total,
            regimes=len(changed_regimes),
        )
        return updated_total

    async def create(
        self,
        shift_data: ShiftTaskCreate,
    ) -> ShiftTask:
        """Создать shift_task с route_tasks.

        Args:
            shift_data: Данные для создания
            db: Database session

        Returns:
            ShiftTask: Созданная смена с загруженными route_tasks
        """
        try:
            # Извлечь данные
            shift_payload = shift_data.model_dump()
            route_tasks_payload = shift_payload.pop("route_tasks", [])

            # Создать ShiftTask
            shift_task = ShiftTask(**shift_payload)
            self.session.add(shift_task)
            await self.session.flush()

            # Создать RouteTask через bulk upsert (один запрос INSERT ... ON CONFLICT)
            if route_tasks_payload:
                normalized = []
                for r in route_tasks_payload:
                    payload = r if isinstance(r, dict) else r.model_dump()
                    item_id = payload.get("id")
                    rest = {k: v for k, v in payload.items() if k not in ("id", "shift_task_id")}
                    normalized.append(RouteTaskBulkUpsertItem(id=item_id, **rest))
                await RouteTaskBulkService.bulk_upsert(
                    data=RouteTaskBulkUpsertRequest(items=normalized),
                    db=self.session,
                    shift_task_id=shift_task.id,
                )
            else:
                await self.session.commit()
            await self.session.refresh(shift_task)
            logger.info(
                "ShiftTask created",
                shift_id=shift_task.id,
                route_tasks_count=len(route_tasks_payload),
            )
            return shift_task

        except Exception as e:
            await self.session.rollback()
            logger.error(
                "ShiftTask create failed",
                error=str(e),
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Create failed: {str(e)}",
            ) from e

    async def update(
        self,
        shift_id: str,
        shift_data: ShiftTaskUpdate,
    ) -> ShiftTask:
        """Обновить shift_task с diff логикой route_tasks.

        ЛОГИКА route_tasks:
        - route_tasks = None → НЕ ТРОГАТЬ существующие
        - route_tasks = [] → УДАЛИТЬ ВСЕ существующие
        - route_tasks = [...] → ПОЛНАЯ ЗАМЕНА:
          * Переданные (с id) → UPDATE
          * Переданные (без id) → CREATE
          * НЕ переданные → DELETE

        Args:
            shift_id: ID смены
            shift_data: Данные для обновления
            db: Database session

        Returns:
            ShiftTask: Обновленная смена с загруженными route_tasks

        Raises:
            HTTPException(404): Если смена не найдена
        """
        try:
            # 1. READ
            shift_task = await self.session.get(ShiftTask, shift_id)
            if not shift_task:
                raise HTTPException(
                    status_code=404,
                    detail=f"ShiftTask {shift_id} not found",
                )
            # 2. UPDATE полей shift_task
            update_payload = shift_data.model_dump(exclude_unset=True)
            route_tasks_payload = update_payload.pop("route_tasks", None)

            for key, value in update_payload.items():
                setattr(shift_task, key, value)

            # 3. Diff логика для route_tasks
            if route_tasks_payload is not None:
                # Загрузить существующие route_tasks
                existing_query = select(RouteTask).where(
                    RouteTask.shift_task_id == shift_task.id,
                )
                existing_result = await self.session.execute(existing_query)
                existing_tasks: dict[str, RouteTask] = {rt.id: rt for rt in existing_result.scalars().all()}

                # Создать мапу переданных задач
                new_tasks_map: dict[str, dict[str, Any]] = {}
                for rt_data in route_tasks_payload:
                    rt_dict = rt_data if isinstance(rt_data, dict) else rt_data.model_dump()
                    rt_id_raw = rt_dict.get("id")
                    rt_id = str(rt_id_raw) if rt_id_raw else generate_uuid()
                    new_tasks_map[rt_id] = rt_dict

                # DELETE: существующие, но не переданные
                to_delete_ids = set(existing_tasks.keys()) - set(new_tasks_map.keys())

                # UPDATE или CREATE через bulk upsert (один запрос INSERT ... ON CONFLICT DO UPDATE)
                _skip_keys = ("id", "shift_task_id", "created_at", "updated_at")
                normalized = []
                for route_id, route_data in new_tasks_map.items():
                    rest = {k: v for k, v in route_data.items() if k not in _skip_keys}
                    normalized.append(RouteTaskBulkUpsertItem(id=route_id, **rest))
                await RouteTaskBulkService.bulk_upsert(
                    data=RouteTaskBulkUpsertRequest(items=normalized),
                    db=self.session,
                    shift_task_id=shift_task.id,
                )

                # DELETE
                if to_delete_ids:
                    await self.session.execute(
                        delete(RouteTask).where(RouteTask.id.in_(to_delete_ids)),
                    )

            # 4. ЯВНЫЙ COMMIT
            if not shift_task.route_tasks:
                await self.session.commit()
            await self.session.refresh(shift_task)
            logger.info(
                "ShiftTask updated",
                shift_id=shift_id,
                route_tasks_updated=route_tasks_payload is not None,
            )

            return shift_task

        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(
                "ShiftTask update failed",
                shift_id=shift_id,
                error=str(e),
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Update failed: {str(e)}",
            ) from e

    async def delete(
        self,
        shift_id: str,
    ) -> ShiftTask:
        """Удалить shift_task (мягкое удаление через статус).

        RouteTask удаляются автоматически через cascade="all, delete-orphan".

        Args:
            shift_id: ID смены
            db: Database session

        Returns:
            ShiftTask: Удаленная смена

        Raises:
            HTTPException(404): Если смена не найдена
        """
        try:
            shift_task = await self.session.get(ShiftTask, shift_id)
            if not shift_task:
                raise HTTPException(
                    status_code=404,
                    detail=f"ShiftTask {shift_id} not found",
                )
            shift_task.status = ShiftTaskStatusEnum.CANCELLED

            # ЯВНЫЙ COMMIT
            await self.session.commit()
            await self.session.refresh(shift_task)
            logger.info("ShiftTask deleted", shift_id=shift_id)
            return shift_task

        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(
                "ShiftTask delete failed",
                shift_id=shift_id,
                error=str(e),
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Delete failed: {str(e)}",
            ) from e

    async def get_by_id(
        self,
        task_id: str,
    ) -> ShiftTask:
        """Получить ShiftTask по ID.

        Args:
            task_id: ID маршрутного задания
            db: Database session

        Returns:
            ShiftTask: Смена с загруженными route_tasks

        Raises:
            HTTPException(404): Если задание не найдено
        """
        # Поиск маршрутного задания и соответствующей смены
        route_task_result = await self.session.execute(
            select(RouteTask).where(RouteTask.id == task_id),
        )
        route_task = route_task_result.scalar_one_or_none()

        if not route_task:
            raise HTTPException(
                status_code=404,
                detail=f"Route task {task_id} not found",
            )
        # Проверить наличие shift_task_id
        if not route_task.shift_task_id:
            raise HTTPException(
                status_code=400,
                detail=f"Route task {task_id} has no shift_task_id",
            )
        # Загрузить shift_task
        shift_task = await self.session.get(ShiftTask, route_task.shift_task_id)
        if not shift_task:
            raise HTTPException(
                status_code=404,
                detail=f"Shift task {route_task.shift_task_id} not found",
            )
        # route_tasks загрузятся автоматически через relationship (lazy="selectin")
        logger.info(
            "ShiftTask retrieved",
            task_id=task_id,
            shift_id=shift_task.id,
            route_tasks_count=len(shift_task.route_tasks),
        )

        return shift_task

    async def list_paginated(
        self,
        page: int,
        size: int,
        status_route_tasks: list[TripStatusRouteEnum] | None = None,
        shift_date: str | None = None,
        vehicle_ids: list[int] | None = None,
        shift_num: int | None = None,
    ) -> tuple[list[ShiftTaskResponse], int]:
        """Получить список смен с пагинацией и фильтрацией.

        route_tasks загружаются автоматически через relationship (lazy="selectin").

        Args:
            page: Номер страницы (начиная с 1)
            size: Размер страницы
            status_route_tasks: Фильтр по статусу route_task (опционально)
            shift_date: Фильтр по дате смены (опционально)
            vehicle_ids: Фильтр по ID транспорта (опционально)
            shift_num: Фильтр по номеру смены (опционально)
            db: Database session

        Returns:
            Tuple[List[ShiftTaskResponse], int]: Список смен (response) и общее количество
        """
        query = select(ShiftTask)
        count_query = select(func.count()).select_from(ShiftTask)

        # Применяем фильтры для ShiftTask
        if status_route_tasks:
            # Фильтр: только те shift_task, у которых есть хотя бы один route_task с нужным статусом
            query = query.where(ShiftTask.route_tasks.any(RouteTask.status.in_(status_route_tasks)))
            count_query = count_query.where(ShiftTask.route_tasks.any(RouteTask.status.in_(status_route_tasks)))

        if shift_date:
            query = query.where(ShiftTask.shift_date == shift_date)
            count_query = count_query.where(ShiftTask.shift_date == shift_date)

        if vehicle_ids:
            query = query.where(ShiftTask.vehicle_id.in_(vehicle_ids))
            count_query = count_query.where(ShiftTask.vehicle_id.in_(vehicle_ids))

        if shift_num is not None:
            query = query.where(ShiftTask.shift_num == shift_num)
            count_query = count_query.where(ShiftTask.shift_num == shift_num)

        # Подсчет общего количества
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # Получение данных с пагинацией
        offset = (page - 1) * size
        query = query.order_by(ShiftTask.created_at.desc()).offset(offset).limit(size)

        result = await self.session.execute(query)
        shift_tasks = result.scalars().all()

        # Преобразуем в response с фильтрацией route_tasks по статусу
        response_items = ShiftTaskService.filter_route_tasks_by_status(
            shift_tasks=list(shift_tasks),
            status_route_tasks=status_route_tasks,
        )

        logger.info(
            "ShiftTasks listed",
            page=page,
            size=size,
            total=total,
            returned=len(response_items),
        )

        return response_items, total

    @staticmethod
    def filter_route_tasks_by_status(
        shift_tasks: list[ShiftTask],
        status_route_tasks: list[TripStatusRouteEnum] | None = None,
    ) -> list[ShiftTaskResponse]:
        """Преобразует список ShiftTask в ShiftTaskResponse с фильтрацией route_tasks по статусу.

        Args:
            shift_tasks: Список ShiftTask из БД
            status_route_tasks: Опциональный фильтр по статусу route_task

        Returns:
            List[ShiftTaskResponse]: Список ответов с отфильтрованными route_tasks
        """
        response_items = []
        for st in shift_tasks:
            shift_task_response = ShiftTaskResponse.model_validate(st)
            # Если указан фильтр по статусу route_task, фильтруем их
            if status_route_tasks:
                shift_task_response.route_tasks = [
                    rt for rt in shift_task_response.route_tasks if rt.status in status_route_tasks
                ]
            response_items.append(shift_task_response)
        return response_items
