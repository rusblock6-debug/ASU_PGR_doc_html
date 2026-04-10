"""Pytest фикстуры для интеграционных тестов tasks.

Использует реальные подключения к БД, MQTT и Redis (или их моки с проверкой).

Чтобы избежать "Future attached to a different loop" при закрытии сессии,
engine и фабрика сессий создаются в session-scoped фикстуре внутри того же
event loop, что и тесты, и явно закрываются в teardown.
"""

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.mqtt_client import TripServiceMQTTClient


@pytest_asyncio.fixture(scope="session")
async def _test_engine_and_session_factory():
    """Session-scoped engine и фабрика сессий, созданные в том же event loop, что и тесты.

    Явный dispose() в teardown устраняет ошибки при закрытии сессии (different loop).
    NullPool избегает привязки пула соединений к другому loop.
    """
    from app.core.config import settings

    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        poolclass=NullPool,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    yield session_factory
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db_session(_test_engine_and_session_factory):
    """Фикстура для тестовой БД.

    Использует фабрику сессий, привязанную к тому же event loop, что и тесты.
    Каждый тест получает новую сессию. После теста сессия закрывается в том же loop.
    """
    async with _test_engine_and_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def mock_mqtt_client():
    """Фикстура для мока MQTT клиента.

    Возвращает мок, который можно проверить на вызовы publish.
    """
    mock_client = AsyncMock(spec=TripServiceMQTTClient)
    mock_client.connect = AsyncMock()
    mock_client.disconnect = AsyncMock()
    mock_client.publish = AsyncMock(return_value=True)
    mock_client.vehicle_id = "test_vehicle"
    return mock_client


@pytest_asyncio.fixture
async def mock_redis_client():
    """Фикстура для мока Redis клиента.

    Возвращает мок, который можно проверить на вызовы publish.
    """
    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=True)
    return mock_redis


@pytest.fixture
def captured_mqtt_messages():
    """Фикстура для захвата MQTT сообщений.

    Возвращает список, в который будут записываться все опубликованные сообщения.
    """
    return []


@pytest.fixture
def captured_redis_messages():
    """Фикстура для захвата Redis сообщений.

    Возвращает список, в который будут записываться все опубликованные сообщения.
    """
    return []
