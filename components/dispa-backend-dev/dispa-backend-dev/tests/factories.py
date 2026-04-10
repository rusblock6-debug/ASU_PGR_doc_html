"""Общие фабрики для создания моков в тестах.

В отличие от моков фабрики генерируют обьект а не эметируют его.
Могут использоваться для создания моков.

Содержит универсальные фабрики для моков, которые используются
во всех доменах:
- AsyncSession (SQLAlchemy)
- RedisClient
- EnterpriseServiceClient
- MQTT клиенты
- FastAPI TestClient
- SQLAlchemy Result объекты
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock

from sqlalchemy.ext.asyncio import AsyncSession


def create_mock_db_session(
    commit_side_effect: Any | None = None,
    rollback_side_effect: Any | None = None,
    flush_side_effect: Any | None = None,
    refresh_side_effect: Any | None = None,
    execute_result: Any | None = None,
    get_result: Any | None = None,
) -> AsyncMock:
    """Создать мок для AsyncSession (SQLAlchemy).

    Args:
        commit_side_effect: Что должно произойти при commit (может быть функция)
        rollback_side_effect: Что должно произойти при rollback
        flush_side_effect: Что должно произойти при flush
        refresh_side_effect: Что должно произойти при refresh
        execute_result: Результат для execute() (Result объект)
        get_result: Результат для get() (модель или None)

    Returns:
        AsyncMock с настроенными методами AsyncSession
    """
    mock_session = AsyncMock(spec=AsyncSession)

    # Настройка commit
    if commit_side_effect:
        mock_session.commit.side_effect = commit_side_effect
    else:
        mock_session.commit = AsyncMock()

    # Настройка rollback
    if rollback_side_effect:
        mock_session.rollback.side_effect = rollback_side_effect
    else:
        mock_session.rollback = AsyncMock()

    # Настройка flush
    if flush_side_effect:
        mock_session.flush.side_effect = flush_side_effect
    else:
        mock_session.flush = AsyncMock()

    # Настройка refresh
    if refresh_side_effect:
        mock_session.refresh.side_effect = refresh_side_effect
    else:
        mock_session.refresh = AsyncMock()

    # Настройка execute
    if execute_result is not None:
        mock_session.execute.return_value = execute_result
    else:
        mock_session.execute = AsyncMock(return_value=MagicMock())

    # Настройка get
    if get_result is not None:
        mock_session.get = AsyncMock(return_value=get_result)
    else:
        mock_session.get = AsyncMock(return_value=None)

    # Настройка add (обычно ничего не возвращает)
    mock_session.add = Mock()

    # Настройка delete (для bulk операций)
    mock_session.delete = AsyncMock()

    # Настройка close (для context manager)
    mock_session.close = AsyncMock()

    # Настройка __aenter__ и __aexit__ для async context manager
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    return mock_session


def create_mock_result(
    scalar_one_return: Any | None = None,
    scalar_one_or_none_return: Any | None = None,
    scalars_return: list | None = None,
    first_return: Any | None = None,
) -> MagicMock:
    """Создать мок для Result объекта SQLAlchemy.

    Args:
        scalar_one_return: Возвращаемое значение для scalar_one()
        scalar_one_or_none_return: Возвращаемое значение для scalar_one_or_none()
        scalars_return: Возвращаемое значение для scalars() (ScalarResult)
        first_return: Возвращаемое значение для first()

    Returns:
        MagicMock с настроенными методами Result
    """
    mock_result = MagicMock()

    if scalar_one_return is not None:
        mock_result.scalar_one.return_value = scalar_one_return
    else:
        mock_result.scalar_one = Mock()

    if scalar_one_or_none_return is not None:
        mock_result.scalar_one_or_none.return_value = scalar_one_or_none_return
    else:
        mock_result.scalar_one_or_none = Mock(return_value=None)

    if scalars_return is not None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = scalars_return
        mock_result.scalars.return_value = mock_scalars
    else:
        mock_result.scalars = Mock(return_value=MagicMock())

    if first_return is not None:
        mock_result.first.return_value = first_return
    else:
        mock_result.first = Mock(return_value=None)

    return mock_result


def create_mock_redis_client(
    get_return: str | None = None,
    get_json_return: dict | None = None,
    set_return: bool = True,
    publish_return: bool = True,
) -> AsyncMock:
    """Создать мок для RedisClient.

    Args:
        get_return: Возвращаемое значение для get()
        get_json_return: Возвращаемое значение для get_json()
        set_return: Возвращаемое значение для set()
        publish_return: Возвращаемое значение для publish()

    Returns:
        AsyncMock с настроенными методами RedisClient
    """
    mock_redis = AsyncMock()

    mock_redis.get = AsyncMock(return_value=get_return)
    mock_redis.get_json = AsyncMock(return_value=get_json_return)
    mock_redis.set = AsyncMock(return_value=set_return)
    mock_redis.set_json = AsyncMock(return_value=set_return)
    mock_redis.delete = AsyncMock(return_value=True)
    mock_redis.publish = AsyncMock(return_value=publish_return)

    # Connection методы
    mock_redis.connect = AsyncMock()
    mock_redis.disconnect = AsyncMock()

    return mock_redis


def create_mock_enterprise_client(
    get_prev_shift_return: dict | None = None,
    get_active_work_regimes_return: list | None = None,
) -> AsyncMock:
    """Создать мок для EnterpriseServiceClient.

    Args:
        get_prev_shift_return: Возвращаемое значение для get_prev_shift()
        get_active_work_regimes_return: Возвращаемое значение для get_active_work_regimes()

    Returns:
        AsyncMock с настроенными методами EnterpriseServiceClient
    """
    mock_client = AsyncMock()

    mock_client.get_prev_shift = AsyncMock(return_value=get_prev_shift_return)
    mock_client.get_active_work_regimes = AsyncMock(return_value=get_active_work_regimes_return or [])

    return mock_client


def create_mock_mqtt_client(
    publish_return: Any | None = None,
    is_connected_return: bool = True,
) -> AsyncMock:
    """Создать мок для MQTT клиента.

    Args:
        publish_return: Возвращаемое значение для publish()
        is_connected_return: Возвращаемое значение для is_connected()

    Returns:
        AsyncMock с настроенными методами MQTT клиента
    """
    mock_mqtt = AsyncMock()

    mock_mqtt.publish = AsyncMock(return_value=publish_return)
    mock_mqtt.is_connected = Mock(return_value=is_connected_return)
    mock_mqtt.connect = AsyncMock()
    mock_mqtt.disconnect = AsyncMock()

    return mock_mqtt
