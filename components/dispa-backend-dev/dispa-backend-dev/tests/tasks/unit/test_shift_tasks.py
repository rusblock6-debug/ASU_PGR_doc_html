"""Unit тесты для ShiftTaskService.

Тестирует отдельные операции с shift_tasks:
- create (создание с route_tasks)
- update (обновление с diff логикой route_tasks)
- delete (мягкое удаление)
- get_by_id (получение по ID route_task)
- list_paginated (список с фильтрацией)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.schemas.tasks.shift_tasks import ShiftTaskCreate, ShiftTaskUpdate
from app.database.models import ShiftTask
from app.enums import ShiftTaskStatusEnum, TypesRouteTaskEnum
from app.services.tasks.shift_task import ShiftTaskService


class TestShiftTaskService:
    """Тесты для ShiftTaskService."""

    @pytest.mark.asyncio
    async def test_create_success(self, db_session, mock_shift_task):
        """Тест create успешное создание."""
        db_session.flush = AsyncMock()
        db_session.refresh = AsyncMock()

        shift_data = ShiftTaskCreate(
            work_regime_id=1,
            vehicle_id=1,
            shift_date="2024-01-01",
            shift_num=1,
            status=ShiftTaskStatusEnum.PENDING,
            route_tasks=[],
        )

        with patch("app.services.tasks.shift_task.generate_short_id", return_value="new_shift_123"):
            with patch(
                "app.services.tasks.shift_task.TaskEventPublisher.publish_shift_task_changed",
                new_callable=AsyncMock,
            ):
                with patch(
                    "app.services.tasks.shift_task.TaskEventPublisher.publish_route_tasks_batch",
                    new_callable=AsyncMock,
                ):
                    result = await ShiftTaskService(db_session).create(
                        shift_data=shift_data,
                    )

        # Проверки
        assert isinstance(result, ShiftTask)
        db_session.add.assert_called()
        db_session.commit.assert_called_once()
        db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_route_tasks(self, db_session):
        """Тест create с вложенными route_tasks."""
        db_session.flush = AsyncMock()

        shift_data = ShiftTaskCreate(
            work_regime_id=1,
            vehicle_id=1,
            shift_date="2024-01-01",
            shift_num=1,
            status=ShiftTaskStatusEnum.PENDING,
            route_tasks=[
                {
                    "route_order": 0,
                    "place_a_id": 1,
                    "place_b_id": 2,
                    "type_task": TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
                },
            ],
        )

        with patch("app.services.tasks.shift_task.generate_short_id", side_effect=["shift_123", "route_123"]):
            with patch(
                "app.services.tasks.shift_task.TaskEventPublisher.publish_shift_task_changed",
                new_callable=AsyncMock,
            ):
                with patch(
                    "app.services.tasks.shift_task.TaskEventPublisher.publish_route_tasks_batch",
                    new_callable=AsyncMock,
                ):
                    result = await ShiftTaskService(db_session).create(
                        shift_data=shift_data,
                    )

        # Проверки
        assert isinstance(result, ShiftTask)
        assert db_session.add.call_count == 2  # shift_task + route_task

    @pytest.mark.asyncio
    async def test_create_rollback_on_error(self, db_session):
        """Тест rollback при ошибке в create."""
        db_session.flush = AsyncMock()
        db_session.commit.side_effect = Exception("Database error")

        shift_data = ShiftTaskCreate(
            work_regime_id=1,
            vehicle_id=1,
            shift_date="2024-01-01",
            shift_num=1,
            status=ShiftTaskStatusEnum.PENDING,
        )

        with patch("app.services.tasks.shift_task.generate_short_id", return_value="shift_error"):
            with pytest.raises(HTTPException) as exc_info:
                await ShiftTaskService(db_session).create(
                    shift_data=shift_data,
                )

        assert exc_info.value.status_code == 500
        db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_success(self, db_session, mock_shift_task):
        """Тест update успешное обновление."""
        db_session.get.return_value = mock_shift_task
        db_session.refresh = AsyncMock()

        # Мок для execute (загрузка существующих route_tasks)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        db_session.execute.return_value = mock_result

        shift_data = ShiftTaskUpdate(
            vehicle_id=2,
            shift_num=2,
        )

        with patch(
            "app.services.tasks.shift_task.TaskEventPublisher.publish_shift_task_changed",
            new_callable=AsyncMock,
        ):
            result = await ShiftTaskService(db_session).update(
                shift_id=mock_shift_task.id,
                shift_data=shift_data,
            )

        # Проверки
        assert isinstance(result, ShiftTask)
        db_session.commit.assert_called_once()
        db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, db_session):
        """Тест update когда shift_task не найден."""
        db_session.get.return_value = None

        shift_data = ShiftTaskUpdate(vehicle_id=2)

        with pytest.raises(HTTPException) as exc_info:
            await ShiftTaskService(db_session).update(
                shift_id="non_existent",
                shift_data=shift_data,
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_update_with_route_tasks_diff(self, db_session, mock_shift_task, mock_route_task):
        """Тест update с DIFF логикой для route_tasks."""
        db_session.get.return_value = mock_shift_task
        db_session.refresh = AsyncMock()

        # Существующие route_tasks
        existing_route = mock_route_task
        existing_route.id = "route_1"

        # Мок для execute (загрузка существующих route_tasks)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [existing_route]
        mock_result.scalars.return_value = mock_scalars
        db_session.execute.return_value = mock_result

        db_session.execute.return_value = mock_result

        shift_data = ShiftTaskUpdate(
            route_tasks=[
                {"id": "route_1", "route_order": 0, "place_a_id": 1, "place_b_id": 2},  # UPDATE
                {"route_order": 1, "place_a_id": 3, "place_b_id": 4},  # CREATE
            ],
        )

        with patch("app.services.tasks.shift_task.generate_short_id", return_value="route_new"):
            with patch(
                "app.services.tasks.shift_task.TaskEventPublisher.publish_shift_task_changed",
                new_callable=AsyncMock,
            ):
                with patch(
                    "app.services.tasks.shift_task.TaskEventPublisher.publish_route_tasks_batch",
                    new_callable=AsyncMock,
                ):
                    result = await ShiftTaskService(db_session).update(
                        shift_id=mock_shift_task.id,
                        shift_data=shift_data,
                    )

        # Проверки
        assert isinstance(result, ShiftTask)
        db_session.execute.assert_called()  # DELETE должен быть вызван для не переданных route_tasks

    @pytest.mark.asyncio
    async def test_delete_success(self, db_session, mock_shift_task):
        """Тест delete успешное удаление."""
        db_session.get.return_value = mock_shift_task
        db_session.refresh = AsyncMock()

        with patch(
            "app.services.tasks.shift_task.TaskEventPublisher.publish_shift_task_changed",
            new_callable=AsyncMock,
        ):
            result = await ShiftTaskService(db_session).delete(
                shift_id=mock_shift_task.id,
            )

        # Проверки
        assert isinstance(result, ShiftTask)
        assert result.status == ShiftTaskStatusEnum.CANCELLED
        db_session.commit.assert_called_once()
        db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, db_session):
        """Тест delete когда shift_task не найден."""
        db_session.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await ShiftTaskService(db_session).delete(
                shift_id="non_existent",
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, db_session, mock_shift_task, mock_route_task):
        """Тест get_by_id успешное получение."""
        # Настроить моки
        mock_route_task.shift_task_id = mock_shift_task.id

        # Мок для execute (поиск route_task)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_route_task
        db_session.execute.return_value = mock_result

        db_session.get.return_value = mock_shift_task

        result = await ShiftTaskService(db_session).get_by_id(
            task_id=mock_route_task.id,
        )

        # Проверки
        assert isinstance(result, ShiftTask)
        assert result.id == mock_shift_task.id
        db_session.execute.assert_called()
        db_session.get.assert_called()

    @pytest.mark.asyncio
    async def test_get_by_id_route_task_not_found(self, db_session):
        """Тест get_by_id когда route_task не найден."""
        # Мок для execute (route_task не найден)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await ShiftTaskService(db_session).get_by_id(
                task_id="non_existent",
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_by_id_no_shift_task_id(self, db_session, mock_route_task):
        """Тест get_by_id когда route_task не имеет shift_task_id."""
        mock_route_task.shift_task_id = None

        # Мок для execute (route_task найден, но без shift_task_id)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_route_task
        db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await ShiftTaskService(db_session).get_by_id(
                task_id=mock_route_task.id,
            )

        assert exc_info.value.status_code == 400
        assert "no shift_task_id" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_list_paginated_success(self, db_session, mock_shift_task):
        """Тест list_paginated успешное получение списка."""
        # Мок для count query
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        db_session.execute.return_value = mock_count_result

        # Мок для data query
        mock_data_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_shift_task]
        mock_data_result.scalars.return_value = mock_scalars

        # Настроить execute для возврата разных результатов
        call_count = [0]

        async def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            # Первый вызов - count query
            if call_count[0] == 1:
                return mock_count_result
            # Второй вызов - data query
            return mock_data_result

        db_session.execute = AsyncMock(side_effect=execute_side_effect)

        tasks, total = await ShiftTaskService(db_session).list_paginated(
            page=1,
            size=10,
        )

        # Проверки
        assert len(tasks) == 1
        assert total == 1
        assert isinstance(tasks[0], ShiftTask)

    @pytest.mark.asyncio
    async def test_list_paginated_with_filters(self, db_session, mock_shift_task):
        """Тест list_paginated с фильтрами."""
        # Мок для count query
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        # Мок для data query
        mock_data_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_shift_task]
        mock_data_result.scalars.return_value = mock_scalars

        call_count = [0]

        async def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_count_result
            return mock_data_result

        db_session.execute = AsyncMock(side_effect=execute_side_effect)

        tasks, total = await ShiftTaskService(db_session).list_paginated(
            page=1,
            size=10,
            status="pending",
            vehicle_id=1,
            shift_num=1,
        )

        # Проверки
        assert len(tasks) == 1
        assert total == 1
