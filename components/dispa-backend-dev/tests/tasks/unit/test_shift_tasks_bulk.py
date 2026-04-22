"""Unit тесты для ShiftTaskBulkService.

Тестирует bulk операции с shift_tasks:
- bulk_upsert (создание + обновление)
- bulk_create (массовое создание)
- bulk_update (массовое обновление)
- Обработка route_tasks (CREATE/UPDATE/DELETE)
- MQTT публикация
- Обработка ошибок
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.schemas.tasks.shift_tasks_bulk import ShiftTaskUpsertItem
from app.database.models import RouteTask, ShiftTask
from app.services.tasks.shift_task_bulk import ShiftTaskBulkService


class TestShiftTaskBulkService:
    """Тесты для ShiftTaskBulkService."""

    @pytest.mark.asyncio
    async def test_bulk_create_success(self, db_session, sample_shift_task_upsert_items):
        """Тест bulk_create успешное создание."""
        # Настроить моки
        db_session.flush = AsyncMock()

        # Моки для RouteTaskBulkService.bulk_create
        with patch(
            "app.services.tasks.shift_task_bulk.RouteTaskBulkService.bulk_create",
            new_callable=AsyncMock,
        ) as mock_route_bulk:
            mock_route_bulk.return_value = []

            with patch("app.services.tasks.shift_task_bulk.generate_short_id", return_value="new_shift_123"):
                # Создать только CREATE items (без id)
                create_items = [item for item in sample_shift_task_upsert_items if not item.id]

                result = await ShiftTaskBulkService.bulk_create(
                    items=create_items,
                    db=db_session,
                )

        # Проверки
        assert len(result) == len(create_items)
        assert all(isinstance(st, ShiftTask) for st in result)
        assert db_session.add.call_count == len(create_items)
        db_session.flush.assert_called()
        db_session.commit.assert_not_called()  # НЕ должен делать commit

    @pytest.mark.asyncio
    async def test_bulk_create_with_route_tasks(self, db_session):
        """Тест bulk_create с вложенными route_tasks."""
        # Настроить моки
        db_session.flush = AsyncMock()

        from app.enums import TypesRouteTaskEnum

        items = [
            ShiftTaskUpsertItem(
                work_regime_id=1,
                vehicle_id=1,
                shift_date="2024-01-01",
                shift_num=1,
                route_tasks=[
                    {
                        "route_order": 0,
                        "place_a_id": 1,
                        "place_b_id": 2,
                        "type_task": TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
                    },
                ],
            ),
        ]

        with patch("app.services.tasks.shift_task_bulk.generate_short_id", return_value="shift_with_routes"):
            with patch(
                "app.services.tasks.shift_task_bulk.RouteTaskBulkService.bulk_create",
                new_callable=AsyncMock,
            ) as mock_route_bulk:
                mock_route_bulk.return_value = []

                result = await ShiftTaskBulkService.bulk_create(
                    items=items,
                    db=db_session,
                )

        # Проверки
        assert len(result) == 1
        mock_route_bulk.assert_called_once()
        db_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_bulk_update_success(self, db_session, mock_shift_task):
        """Тест bulk_update успешное обновление."""
        # Настроить моки
        db_session.get.return_value = mock_shift_task

        # Мок для execute (загрузка существующих route_tasks)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        db_session.execute.return_value = mock_result

        items = [
            ShiftTaskUpsertItem(
                id=mock_shift_task.id,
                vehicle_id=2,
                shift_num=2,
            ),
        ]

        with patch("app.services.tasks.shift_task_bulk.RouteTaskBulkService.bulk_update", new_callable=AsyncMock):
            with patch("app.services.tasks.shift_task_bulk.RouteTaskBulkService.bulk_create", new_callable=AsyncMock):
                updated_tasks, deleted_count = await ShiftTaskBulkService.bulk_update(
                    items=items,
                    db=db_session,
                )

        # Проверки
        assert len(updated_tasks) == 1
        assert deleted_count == 0
        db_session.get.assert_called()
        db_session.commit.assert_not_called()  # НЕ должен делать commit

    @pytest.mark.asyncio
    async def test_bulk_update_missing_id(self, db_session):
        """Тест bulk_update без id."""
        items = [
            ShiftTaskUpsertItem(
                # id отсутствует
                vehicle_id=1,
                shift_date="2024-01-01",
                shift_num=1,
            ),
        ]

        with pytest.raises(HTTPException) as exc_info:
            await ShiftTaskBulkService.bulk_update(
                items=items,
                db=db_session,
            )

        assert exc_info.value.status_code == 400
        assert "requires id" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_bulk_update_not_found(self, db_session):
        """Тест bulk_update когда shift_task не найден."""
        db_session.get.return_value = None

        items = [
            ShiftTaskUpsertItem(
                id="non_existent",
                vehicle_id=1,
                shift_date="2024-01-01",
                shift_num=1,
            ),
        ]

        with pytest.raises(HTTPException) as exc_info:
            await ShiftTaskBulkService.bulk_update(
                items=items,
                db=db_session,
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_bulk_update_with_route_tasks_diff(self, db_session, mock_shift_task, mock_route_task):
        """Тест bulk_update с DIFF логикой для route_tasks."""
        # Настроить моки
        db_session.get.return_value = mock_shift_task

        # Существующие route_tasks
        existing_route_1 = mock_route_task
        existing_route_1.id = "route_1"
        existing_route_2 = MagicMock(spec=RouteTask)
        existing_route_2.id = "route_2"

        # Мок для execute (загрузка существующих route_tasks)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [existing_route_1, existing_route_2]
        mock_result.scalars.return_value = mock_scalars
        db_session.execute.return_value = mock_result

        from app.enums import TypesRouteTaskEnum

        items = [
            ShiftTaskUpsertItem(
                id=mock_shift_task.id,
                route_tasks=[
                    {
                        "id": "route_1",
                        "route_order": 0,
                        "place_a_id": 1,
                        "place_b_id": 2,
                        "type_task": TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
                    },  # UPDATE
                    {
                        "route_order": 1,
                        "place_a_id": 3,
                        "place_b_id": 4,
                        "type_task": TypesRouteTaskEnum.LOADING_SHAS,
                    },  # CREATE
                    # route_2 не передан - должен быть DELETE
                ],
            ),
        ]

        with patch("app.services.tasks.shift_task_bulk.RouteTaskBulkService.bulk_update", new_callable=AsyncMock):
            with patch("app.services.tasks.shift_task_bulk.RouteTaskBulkService.bulk_create", new_callable=AsyncMock):
                updated_tasks, deleted_count = await ShiftTaskBulkService.bulk_update(
                    items=items,
                    db=db_session,
                )

        # Проверки
        assert len(updated_tasks) == 1
        assert deleted_count == 1  # route_2 должен быть удален
        db_session.execute.assert_called()  # DELETE должен быть вызван

    @pytest.mark.asyncio
    async def test_bulk_upsert_create_only(self, db_session, sample_shift_task_upsert_items):
        """Тест bulk_upsert только с созданием."""
        db_session.flush = AsyncMock()

        # Создать только CREATE items (без id)
        create_items = [item for item in sample_shift_task_upsert_items if not item.id]

        with patch("app.services.tasks.shift_task_bulk.generate_short_id", return_value="new_shift_456"):
            with patch("app.services.tasks.shift_task_bulk.RouteTaskBulkService.bulk_create", new_callable=AsyncMock):
                with patch(
                    "app.services.tasks.shift_task_bulk.TaskEventPublisher.publish_shift_task_changed",
                    new_callable=AsyncMock,
                ):
                    with patch(
                        "app.services.tasks.shift_task_bulk.TaskEventPublisher.publish_route_tasks_batch",
                        new_callable=AsyncMock,
                    ):
                        result = await ShiftTaskBulkService.bulk_upsert(
                            items=create_items,
                            db=db_session,
                            publish_mqtt=True,
                        )

        # Проверки - BulkResponse содержит только items
        from app.api.schemas.common import BulkResponse

        assert isinstance(result, BulkResponse)
        assert len(result.items) == len(create_items)
        # Подсчитываем created/updated
        created_count = sum(1 for item in result.items if item.action == "created")
        updated_count = sum(1 for item in result.items if item.action == "updated")
        assert created_count == len(create_items)
        assert updated_count == 0
        db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_upsert_update_only(self, db_session, mock_shift_task):
        """Тест bulk_upsert только с обновлением."""
        db_session.get.return_value = mock_shift_task

        # Мок для execute (загрузка существующих route_tasks)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        db_session.execute.return_value = mock_result

        items = [
            ShiftTaskUpsertItem(
                id=mock_shift_task.id,
                vehicle_id=2,
            ),
        ]

        with patch("app.services.tasks.shift_task_bulk.RouteTaskBulkService.bulk_update", new_callable=AsyncMock):
            with patch("app.services.tasks.shift_task_bulk.RouteTaskBulkService.bulk_create", new_callable=AsyncMock):
                with patch(
                    "app.services.tasks.shift_task_bulk.TaskEventPublisher.publish_shift_task_changed",
                    new_callable=AsyncMock,
                ):
                    with patch(
                        "app.services.tasks.shift_task_bulk.TaskEventPublisher.publish_route_tasks_batch",
                        new_callable=AsyncMock,
                    ):
                        result = await ShiftTaskBulkService.bulk_upsert(
                            items=items,
                            db=db_session,
                            publish_mqtt=True,
                        )

        # Проверки - BulkResponse содержит только items
        from app.api.schemas.common import BulkResponse

        assert isinstance(result, BulkResponse)
        assert len(result.items) == 1
        assert result.items[0].action == "updated"
        # Подсчитываем created/updated
        created_count = sum(1 for item in result.items if item.action == "created")
        updated_count = sum(1 for item in result.items if item.action == "updated")
        assert created_count == 0
        assert updated_count == 1
        db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_upsert_mixed(self, db_session, mock_shift_task):
        """Тест bulk_upsert с созданием и обновлением."""
        db_session.flush = AsyncMock()
        db_session.get.return_value = mock_shift_task

        # Мок для execute (загрузка существующих route_tasks)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        db_session.execute.return_value = mock_result

        items = [
            ShiftTaskUpsertItem(
                work_regime_id=1,
                vehicle_id=1,
                shift_date="2024-01-01",
                shift_num=1,
            ),
            ShiftTaskUpsertItem(
                id=mock_shift_task.id,
                vehicle_id=2,
            ),
        ]

        with patch("app.services.tasks.shift_task_bulk.generate_short_id", return_value="new_shift_789"):
            with patch("app.services.tasks.shift_task_bulk.RouteTaskBulkService.bulk_create", new_callable=AsyncMock):
                with patch(
                    "app.services.tasks.shift_task_bulk.RouteTaskBulkService.bulk_update",
                    new_callable=AsyncMock,
                ):
                    with patch(
                        "app.services.tasks.shift_task_bulk.TaskEventPublisher.publish_shift_task_changed",
                        new_callable=AsyncMock,
                    ):
                        with patch(
                            "app.services.tasks.shift_task_bulk.TaskEventPublisher.publish_route_tasks_batch",
                            new_callable=AsyncMock,
                        ):
                            result = await ShiftTaskBulkService.bulk_upsert(
                                items=items,
                                db=db_session,
                                publish_mqtt=True,
                            )

        # Проверки - BulkResponse содержит только items
        from app.api.schemas.common import BulkResponse

        assert isinstance(result, BulkResponse)
        assert len(result.items) == 2
        # Подсчитываем created/updated
        created_count = sum(1 for item in result.items if item.action == "created")
        updated_count = sum(1 for item in result.items if item.action == "updated")
        assert created_count == 1
        assert updated_count == 1
        db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_upsert_rollback_on_error(self, db_session, sample_shift_task_upsert_items):
        """Тест rollback при ошибке в bulk_upsert."""
        db_session.flush = AsyncMock()
        db_session.commit.side_effect = Exception("Database error")

        create_items = [item for item in sample_shift_task_upsert_items if not item.id]

        with patch("app.services.tasks.shift_task_bulk.generate_short_id", return_value="new_shift_error"):
            with patch("app.services.tasks.shift_task_bulk.RouteTaskBulkService.bulk_create", new_callable=AsyncMock):
                with pytest.raises(HTTPException) as exc_info:
                    await ShiftTaskBulkService.bulk_upsert(
                        items=create_items,
                        db=db_session,
                        publish_mqtt=False,
                    )

        assert exc_info.value.status_code == 500
        db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_upsert_without_mqtt(self, db_session, sample_shift_task_upsert_items):
        """Тест bulk_upsert без MQTT публикации."""
        db_session.flush = AsyncMock()

        create_items = [item for item in sample_shift_task_upsert_items if not item.id]

        with patch("app.services.tasks.shift_task_bulk.generate_short_id", return_value="new_shift_no_mqtt"):
            with patch("app.services.tasks.shift_task_bulk.RouteTaskBulkService.bulk_create", new_callable=AsyncMock):
                result = await ShiftTaskBulkService.bulk_upsert(
                    items=create_items,
                    db=db_session,
                    publish_mqtt=False,  # Без MQTT
                )

        from app.api.schemas.common import BulkResponse

        assert isinstance(result, BulkResponse)
        assert len(result.items) == len(create_items)
        assert all(item.action == "created" for item in result.items)
        # TaskEventPublisher не должен вызываться
        # (проверка через отсутствие ошибок)
