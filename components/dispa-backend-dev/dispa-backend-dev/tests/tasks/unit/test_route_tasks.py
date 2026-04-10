"""Unit тесты для RouteTaskService.

Тестирует отдельные операции с route_tasks:
- create (создание)
- update (обновление)
- get_by_id (получение по ID)
- activate (активация)
- delete (мягкое удаление)
- list_paginated (список с фильтрацией)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.schemas.tasks.route_tasks import RouteTaskCreate, RouteTaskUpdate
from app.database.models import RouteTask
from app.enums import TripStatusRouteEnum, TypesRouteTaskEnum
from app.services.tasks.route_task import RouteTaskService


class TestRouteTaskService:
    """Тесты для RouteTaskService."""

    @pytest.mark.asyncio
    async def test_create_success(self, db_session, mock_shift_task):
        """Тест create успешное создание."""
        # Настроить моки
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # route_task не существует
        db_session.execute.return_value = mock_result
        db_session.get.return_value = mock_shift_task  # shift_task существует
        db_session.refresh = AsyncMock()

        route_data = RouteTaskCreate(
            shift_task_id=mock_shift_task.id,
            route_order=0,
            place_a_id=1,
            place_b_id=2,
            type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
            planned_trips_count=1,
        )

        with patch("app.services.tasks.route_task.generate_short_id", return_value="new_route_123"):
            with patch(
                "app.services.tasks.route_task.TaskEventPublisher.publish_route_task_changed",
                new_callable=AsyncMock,
            ):
                result = await RouteTaskService(db_session).create(
                    route_data=route_data,
                )

        # Проверки
        assert isinstance(result, RouteTask)
        db_session.add.assert_called()
        db_session.commit.assert_called_once()
        db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_missing_shift_task_id(self, db_session):
        """Тест create без shift_task_id - Pydantic валидация должна выбросить ошибку."""
        from pydantic import ValidationError

        # Pydantic валидация должна выбросить ошибку при создании схемы без shift_task_id
        # так как shift_task_id является обязательным полем (Field(...))
        with pytest.raises(ValidationError) as exc_info:
            RouteTaskCreate(
                # shift_task_id отсутствует
                route_order=0,
                place_a_id=1,
                place_b_id=2,
                type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
            )

        # Проверяем, что ошибка связана с shift_task_id
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("shift_task_id",) for error in errors)

    @pytest.mark.asyncio
    async def test_create_shift_task_not_found(self, db_session):
        """Тест create когда shift_task не найден."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute.return_value = mock_result
        db_session.get.return_value = None  # shift_task не найден

        route_data = RouteTaskCreate(
            shift_task_id="non_existent",
            route_order=0,
            place_a_id=1,
            place_b_id=2,
            type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
        )

        with patch("app.services.tasks.route_task.generate_short_id", return_value="route_123"):
            with pytest.raises(HTTPException) as exc_info:
                await RouteTaskService(db_session).create(
                    route_data=route_data,
                )

        assert exc_info.value.status_code == 404
        assert "shifttask" in exc_info.value.detail.lower() or "shift_task" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_rollback_on_error(self, db_session, mock_shift_task):
        """Тест rollback при ошибке в create."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute.return_value = mock_result
        db_session.get.return_value = mock_shift_task
        db_session.commit.side_effect = Exception("Database error")

        route_data = RouteTaskCreate(
            shift_task_id=mock_shift_task.id,
            route_order=0,
            place_a_id=1,
            place_b_id=2,
            type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
        )

        with patch("app.services.tasks.route_task.generate_short_id", return_value="route_error"):
            with pytest.raises(HTTPException) as exc_info:
                await RouteTaskService(db_session).create(
                    route_data=route_data,
                )

        assert exc_info.value.status_code == 500
        db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_success(self, db_session, mock_route_task):
        """Тест update успешное обновление."""
        db_session.get.return_value = mock_route_task
        db_session.refresh = AsyncMock()

        route_data = RouteTaskUpdate(
            route_order=1,
            planned_trips_count=5,
        )

        with patch(
            "app.services.tasks.route_task.TaskEventPublisher.publish_route_task_changed",
            new_callable=AsyncMock,
        ):
            result = await RouteTaskService(db_session).update(
                route_id=mock_route_task.id,
                route_data=route_data,
            )

        # Проверки
        assert isinstance(result, RouteTask)
        db_session.commit.assert_called_once()
        db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, db_session):
        """Тест update когда route_task не найден."""
        db_session.get.return_value = None

        route_data = RouteTaskUpdate(route_order=1)

        with pytest.raises(HTTPException) as exc_info:
            await RouteTaskService(db_session).update(
                route_id="non_existent",
                route_data=route_data,
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, db_session, mock_route_task):
        """Тест get_by_id успешное получение."""
        db_session.get.return_value = mock_route_task

        result = await RouteTaskService(db_session).get_by_id(
            route_id=mock_route_task.id,
        )

        # Проверки
        assert isinstance(result, RouteTask)
        assert result.id == mock_route_task.id
        db_session.get.assert_called_once_with(RouteTask, mock_route_task.id)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, db_session):
        """Тест get_by_id когда route_task не найден."""
        db_session.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await RouteTaskService(db_session).get_by_id(
                route_id="non_existent",
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_activate_success(self, db_session, mock_route_task):
        """Тест activate успешная активация."""
        db_session.get.return_value = mock_route_task
        db_session.refresh = AsyncMock()

        with patch("app.services.tasks.route_task.set_active_task", new_callable=AsyncMock) as mock_set_active:
            mock_set_active.return_value = {"success": True}

            result = await RouteTaskService(db_session).activate(
                route_id=mock_route_task.id,
                vehicle_id="vehicle_123",
            )

        # Проверки
        assert isinstance(result, RouteTask)
        mock_set_active.assert_called_once()
        db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_success(self, db_session, mock_route_task):
        """Тест delete успешное удаление."""
        db_session.get.return_value = mock_route_task

        with patch(
            "app.services.tasks.route_task.TaskEventPublisher.publish_route_task_changed",
            new_callable=AsyncMock,
        ):
            await RouteTaskService(db_session).delete(
                route_id=mock_route_task.id,
            )

        # Проверки
        assert mock_route_task.status == TripStatusRouteEnum.REJECTED
        db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, db_session):
        """Тест delete когда route_task не найден."""
        db_session.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await RouteTaskService(db_session).delete(
                route_id="non_existent",
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_list_paginated_success(self, db_session, mock_route_task):
        """Тест list_paginated успешное получение списка."""
        # Мок для count query
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        # Мок для data query
        mock_data_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_route_task]
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

        tasks, total = await RouteTaskService(db_session).list_paginated(
            page=1,
            size=10,
        )

        # Проверки
        assert len(tasks) == 1
        assert total == 1
        assert isinstance(tasks[0], RouteTask)

    @pytest.mark.asyncio
    async def test_list_paginated_with_filters(self, db_session, mock_route_task):
        """Тест list_paginated с фильтрами."""
        # Мок для count query
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        # Мок для data query
        mock_data_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_route_task]
        mock_data_result.scalars.return_value = mock_scalars

        call_count = [0]

        async def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_count_result
            return mock_data_result

        db_session.execute = AsyncMock(side_effect=execute_side_effect)

        tasks, total = await RouteTaskService(db_session).list_paginated(
            page=1,
            size=10,
            shift_task_id="shift_123",
            status=TripStatusRouteEnum.EMPTY,
        )

        # Проверки
        assert len(tasks) == 1
        assert total == 1
