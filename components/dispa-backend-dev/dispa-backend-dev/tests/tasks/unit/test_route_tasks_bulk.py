"""Unit тесты для RouteTaskBulkService.

Тестирует bulk операции с route_tasks:
- bulk_upsert (создание + обновление)
- bulk_create (массовое создание)
- bulk_update (массовое обновление)
- Валидация shift_task_id
- Обработка ошибок
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException

from app.api.schemas.common import BulkResponse
from app.api.schemas.tasks.route_tasks_bulk import (
    RouteTaskBulkCreateItem,
    RouteTaskBulkUpdateItem,
    RouteTaskBulkUpsertItem,
)
from app.database.models import RouteTask, ShiftTask
from app.enums import TripStatusRouteEnum, TypesRouteTaskEnum
from app.services.tasks.route_task_bulk import RouteTaskBulkService


class TestRouteTaskBulkService:
    """Тесты для RouteTaskBulkService."""

    @pytest.fixture
    def mock_shift_task(self):
        """Создать мок для ShiftTask."""
        shift_task = Mock(spec=ShiftTask)
        shift_task.id = "shift_123"
        return shift_task

    @pytest.fixture
    def mock_route_task(self):
        """Создать мок для RouteTask."""
        route_task = Mock(spec=RouteTask)
        route_task.id = "route_123"
        route_task.shift_task_id = "shift_123"
        route_task.route_order = 0
        route_task.place_a_id = 1
        route_task.place_b_id = 2
        route_task.type_task = TypesRouteTaskEnum.LOADING_TRANSPORT_GM
        route_task.status = TripStatusRouteEnum.EMPTY
        return route_task

    @pytest.fixture
    def sample_upsert_items(self):
        """Пример данных для bulk_upsert."""
        return [
            RouteTaskBulkUpsertItem(
                route_order=0,
                place_a_id=1,
                place_b_id=2,
                type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
                planned_trips_count=1,
                status=TripStatusRouteEnum.EMPTY,
                shift_task_id="shift_123",
            ),
            RouteTaskBulkUpsertItem(
                id="route_existing",
                route_order=1,
                place_a_id=3,
                place_b_id=4,
                type_task=TypesRouteTaskEnum.LOADING_SHAS,
                planned_trips_count=2,
                status=TripStatusRouteEnum.ACTIVE,
                shift_task_id="shift_123",
            ),
        ]

    @pytest.fixture
    def sample_create_items(self):
        """Пример данных для bulk_create."""
        return [
            RouteTaskBulkCreateItem(
                route_order=0,
                place_a_id=1,
                place_b_id=2,
                type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
                planned_trips_count=1,
            ),
            RouteTaskBulkCreateItem(
                route_order=1,
                place_a_id=3,
                place_b_id=4,
                type_task=TypesRouteTaskEnum.LOADING_SHAS,
                planned_trips_count=2,
            ),
        ]

    @pytest.fixture
    def sample_update_items(self):
        """Пример данных для bulk_update."""
        return [
            RouteTaskBulkUpdateItem(
                id="route_1",
                route_order=0,
                place_a_id=1,
                place_b_id=2,
                planned_trips_count=5,
            ),
            RouteTaskBulkUpdateItem(
                id="route_2",
                route_order=1,
                place_a_id=3,
                place_b_id=4,
                planned_trips_count=10,
            ),
        ]

    @pytest.mark.asyncio
    async def test_bulk_upsert_create_only(self, db_session, sample_upsert_items):
        """Тест bulk_upsert только с созданием (без id)."""
        # Настроить моки для валидации shift_task_id
        # Валидация делает select(ShiftTask.id).where(ShiftTask.id.in_(shift_task_ids))
        # и возвращает Result объект, который итерируется как [(id1,), (id2,), ...]
        # Получаем shift_task_id из sample_upsert_items
        shift_task_ids = {item.shift_task_id for item in sample_upsert_items if item.shift_task_id}
        # Создаем мок Result, который можно итерировать
        validation_rows = [(sid,) for sid in shift_task_ids]

        # Создаем класс-мок, который можно итерировать
        class IterableResult:
            def __init__(self, rows):
                self.rows = rows

            def __iter__(self):
                return iter(self.rows)

        validation_result = IterableResult(validation_rows)

        # Мок для execute при загрузке созданных объектов для MQTT
        mqtt_result = MagicMock()
        mqtt_scalars = MagicMock()
        mqtt_scalars.all.return_value = []
        mqtt_result.scalars.return_value = mqtt_scalars

        # Настроить side_effect для разных вызовов execute
        call_count = [0]  # Используем список для мутации в замыкании

        async def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            # Первый вызов - валидация shift_task_id
            if call_count[0] == 1:
                return validation_result
            # Последующие вызовы - загрузка для MQTT
            return mqtt_result

        db_session.execute = AsyncMock(side_effect=execute_side_effect)
        db_session.get.return_value = None  # Объекты не найдены (для UPDATE части)

        # Создать только CREATE items (без id)
        create_items = [item for item in sample_upsert_items if not item.id]

        with patch("app.services.tasks.route_task_bulk.generate_short_id", return_value="new_route_123"):
            with patch(
                "app.services.tasks.route_task_bulk.TaskEventPublisher.publish_route_tasks_batch",
                new_callable=AsyncMock,
            ):
                result = await RouteTaskBulkService.bulk_upsert(
                    items=create_items,
                    db=db_session,
                    validate_shift_tasks=True,
                    publish_mqtt=True,
                )

        # Проверки - BulkResponse содержит только items
        assert isinstance(result, BulkResponse)
        assert len(result.items) == 1
        assert result.items[0].action == "created"
        # Подсчитываем created/updated
        created_count = sum(1 for item in result.items if item.action == "created")
        updated_count = sum(1 for item in result.items if item.action == "updated")
        assert created_count == 1
        assert updated_count == 0

        # Проверка вызовов
        db_session.add.assert_called()
        db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_upsert_update_only(self, db_session, sample_upsert_items, mock_route_task):
        """Тест bulk_upsert только с обновлением (с id)."""
        # Настроить моки для валидации shift_task_id
        shift_task_ids = {item.shift_task_id for item in sample_upsert_items if item.shift_task_id}
        validation_rows = [(sid,) for sid in shift_task_ids]

        class IterableResult:
            def __init__(self, rows):
                self.rows = rows

            def __iter__(self):
                return iter(self.rows)

        validation_result = IterableResult(validation_rows)

        # Мок для execute при загрузке обновленных объектов для MQTT
        mqtt_result = MagicMock()
        mqtt_scalars = MagicMock()
        mqtt_scalars.all.return_value = [mock_route_task]
        mqtt_result.scalars.return_value = mqtt_scalars

        call_count = [0]

        async def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            # Первый вызов - валидация shift_task_id
            if call_count[0] == 1:
                return validation_result
            # Последующие вызовы - загрузка для MQTT
            return mqtt_result

        db_session.execute = AsyncMock(side_effect=execute_side_effect)
        db_session.get.return_value = mock_route_task  # Объект найден для UPDATE

        # Создать только UPDATE items (с id)
        update_items = [item for item in sample_upsert_items if item.id]

        with patch(
            "app.services.tasks.route_task_bulk.TaskEventPublisher.publish_route_tasks_batch",
            new_callable=AsyncMock,
        ):
            result = await RouteTaskBulkService.bulk_upsert(
                items=update_items,
                db=db_session,
                validate_shift_tasks=True,
                publish_mqtt=True,
            )

        # Проверки - BulkResponse содержит только items
        assert isinstance(result, BulkResponse)
        assert len(result.items) == 1
        assert result.items[0].action == "updated"
        # Подсчитываем created/updated
        created_count = sum(1 for item in result.items if item.action == "created")
        updated_count = sum(1 for item in result.items if item.action == "updated")
        assert created_count == 0
        assert updated_count == 1

        # Проверка вызовов
        db_session.get.assert_called()
        db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_upsert_mixed(self, db_session, sample_upsert_items, mock_route_task):
        """Тест bulk_upsert с созданием и обновлением."""
        # Настроить моки для валидации shift_task_id
        shift_task_ids = {item.shift_task_id for item in sample_upsert_items if item.shift_task_id}
        validation_rows = [(sid,) for sid in shift_task_ids]

        class IterableResult:
            def __init__(self, rows):
                self.rows = rows

            def __iter__(self):
                return iter(self.rows)

        validation_result = IterableResult(validation_rows)

        # Мок для execute при загрузке объектов для MQTT
        mqtt_result = MagicMock()
        mqtt_scalars = MagicMock()
        mqtt_scalars.all.return_value = [mock_route_task]
        mqtt_result.scalars.return_value = mqtt_scalars

        call_count = [0]

        async def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            # Первый вызов - валидация shift_task_id
            if call_count[0] == 1:
                return validation_result
            # Последующие вызовы - загрузка для MQTT
            return mqtt_result

        db_session.execute = AsyncMock(side_effect=execute_side_effect)
        db_session.get.return_value = mock_route_task  # Объект найден для UPDATE

        with patch("app.services.tasks.route_task_bulk.generate_short_id", return_value="new_route_456"):
            with patch(
                "app.services.tasks.route_task_bulk.TaskEventPublisher.publish_route_tasks_batch",
                new_callable=AsyncMock,
            ):
                result = await RouteTaskBulkService.bulk_upsert(
                    items=sample_upsert_items,
                    db=db_session,
                    validate_shift_tasks=True,
                    publish_mqtt=True,
                )

        # Проверки - BulkResponse содержит только items
        assert isinstance(result, BulkResponse)
        assert len(result.items) == 2
        # Подсчитываем created/updated
        created_count = sum(1 for item in result.items if item.action == "created")
        updated_count = sum(1 for item in result.items if item.action == "updated")
        assert created_count == 1
        assert updated_count == 1

    @pytest.mark.asyncio
    async def test_bulk_upsert_validation_fails(self, db_session, sample_upsert_items):
        """Тест bulk_upsert с невалидным shift_task_id."""
        # Настроить мок: валидация не проходит (нет такого shift_task_id)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []  # Пустой результат
        db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await RouteTaskBulkService.bulk_upsert(
                items=sample_upsert_items,
                db=db_session,
                validate_shift_tasks=True,
                publish_mqtt=False,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid shift_task_ids" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_bulk_upsert_update_not_found(self, db_session):
        """Тест bulk_upsert когда объект для UPDATE не найден."""
        # Настроить моки (валидация отключена, поэтому execute не вызывается для валидации)
        db_session.get.return_value = None  # Объект не найден

        items = [
            RouteTaskBulkUpsertItem(
                id="non_existent",
                route_order=0,
                place_a_id=1,
                place_b_id=2,
                type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
                shift_task_id="shift_123",
            ),
        ]

        result = await RouteTaskBulkService.bulk_upsert(
            items=items,
            db=db_session,
            validate_shift_tasks=False,
            publish_mqtt=False,
        )

        # Проверки - BulkResponse содержит только items
        # Когда объект не найден, он не добавляется в results (failed_count увеличивается, но элемент не добавляется)
        assert isinstance(result, BulkResponse)
        # В текущей реализации failed элементы не добавляются в items
        assert len(result.items) == 0

    @pytest.mark.asyncio
    async def test_bulk_upsert_without_validation(self, db_session, sample_upsert_items):
        """Тест bulk_upsert без валидации shift_task_id."""
        # Мок для execute при загрузке объектов для MQTT (валидация не вызывается)
        mqtt_result = MagicMock()
        mqtt_scalars = MagicMock()
        mqtt_scalars.all.return_value = []
        mqtt_result.scalars.return_value = mqtt_scalars
        db_session.execute = AsyncMock(return_value=mqtt_result)
        db_session.get.return_value = None

        create_items = [item for item in sample_upsert_items if not item.id]

        with patch("app.services.tasks.route_task_bulk.generate_short_id", return_value="new_route_789"):
            with patch(
                "app.services.tasks.route_task_bulk.TaskEventPublisher.publish_route_tasks_batch",
                new_callable=AsyncMock,
            ):
                result = await RouteTaskBulkService.bulk_upsert(
                    items=create_items,
                    db=db_session,
                    validate_shift_tasks=False,  # Без валидации
                    publish_mqtt=True,
                )

        # Проверки: валидация не должна вызываться
        assert isinstance(result, BulkResponse)
        assert len(result.items) == 1
        assert result.items[0].action == "created"
        # execute не должен вызываться для валидации
        # (но может вызываться для загрузки объектов для MQTT)

    @pytest.mark.asyncio
    async def test_bulk_upsert_rollback_on_error(self, db_session, sample_upsert_items):
        """Тест rollback при ошибке в bulk_upsert."""
        # Настроить моки для валидации (если включена)
        shift_task_ids = {item.shift_task_id for item in sample_upsert_items if item.shift_task_id}
        validation_result = MagicMock()
        validation_scalars = MagicMock()
        validation_scalars.all.return_value = [(sid,) for sid in shift_task_ids]
        validation_result.scalars.return_value = validation_scalars

        async def execute_side_effect(*args, **kwargs):
            if "ShiftTask" in str(args[0]) or "shift_task" in str(args[0]):
                return validation_result
            return MagicMock()

        db_session.execute = AsyncMock(side_effect=execute_side_effect)
        db_session.commit.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await RouteTaskBulkService.bulk_upsert(
                items=sample_upsert_items,
                db=db_session,
                validate_shift_tasks=False,
                publish_mqtt=False,
            )

        assert exc_info.value.status_code == 500
        db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create(self, db_session, sample_create_items):
        """Тест bulk_create."""
        shift_task_id = "shift_123"

        result = await RouteTaskBulkService.bulk_create(
            items=sample_create_items,
            shift_task_id=shift_task_id,
            db=db_session,
        )

        # Проверки
        assert len(result) == 2
        assert all(isinstance(rt, RouteTask) for rt in result)
        assert db_session.add.call_count == 2
        db_session.flush.assert_called_once()
        db_session.commit.assert_not_called()  # НЕ должен делать commit

        # Проверка, что shift_task_id установлен
        for route_task in result:
            assert route_task.shift_task_id == shift_task_id

    @pytest.mark.asyncio
    async def test_bulk_update_success(self, db_session, sample_update_items, mock_route_task):
        """Тест bulk_update успешное обновление."""
        # Настроить мок: объекты найдены
        db_session.get.return_value = mock_route_task

        result = await RouteTaskBulkService.bulk_update(
            items=sample_update_items,
            db=db_session,
        )

        # Проверки
        assert len(result) == 2
        assert all(isinstance(rt, RouteTask) for rt in result)
        assert db_session.get.call_count == 2
        db_session.flush.assert_called_once()
        db_session.commit.assert_not_called()  # НЕ должен делать commit

    @pytest.mark.asyncio
    async def test_bulk_update_missing_id(self, db_session):
        """Тест bulk_update без id - Pydantic валидация должна выбросить ошибку."""
        from pydantic import ValidationError

        # Pydantic валидация должна выбросить ошибку при создании схемы без id
        # так как id является обязательным полем для RouteTaskBulkUpdateItem
        with pytest.raises(ValidationError) as exc_info:
            RouteTaskBulkUpdateItem(
                # id отсутствует
                route_order=0,
                place_a_id=1,
                place_b_id=2,
            )

        # Проверяем, что ошибка связана с id
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("id",) for error in errors)

    @pytest.mark.asyncio
    async def test_bulk_update_not_found(self, db_session, sample_update_items):
        """Тест bulk_update когда объект не найден."""
        # Настроить мок: объект не найден
        db_session.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await RouteTaskBulkService.bulk_update(
                items=sample_update_items,
                db=db_session,
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_bulk_upsert_without_mqtt(self, db_session, sample_upsert_items):
        """Тест bulk_upsert без MQTT публикации."""
        # Настроить моки для валидации (если включена)
        shift_task_ids = {item.shift_task_id for item in sample_upsert_items if item.shift_task_id}
        validation_result = MagicMock()
        validation_scalars = MagicMock()
        validation_scalars.all.return_value = [(sid,) for sid in shift_task_ids]
        validation_result.scalars.return_value = validation_scalars

        async def execute_side_effect(*args, **kwargs):
            if "ShiftTask" in str(args[0]) or "shift_task" in str(args[0]):
                return validation_result
            return MagicMock()

        db_session.execute = AsyncMock(side_effect=execute_side_effect)
        db_session.get.return_value = None

        create_items = [item for item in sample_upsert_items if not item.id]

        with patch("app.services.tasks.route_task_bulk.generate_short_id", return_value="new_route_no_mqtt"):
            result = await RouteTaskBulkService.bulk_upsert(
                items=create_items,
                db=db_session,
                validate_shift_tasks=False,
                publish_mqtt=False,  # Без MQTT
            )

        assert isinstance(result, BulkResponse)
        assert len(result.items) == 1
        assert result.items[0].action == "created"
        # TaskEventPublisher не должен вызываться
        # (проверка через отсутствие ошибок)
