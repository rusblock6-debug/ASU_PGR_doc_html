# ruff: noqa: D100, D101, D102, D103
import asyncio
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from functools import partial

from clickhouse_connect import get_client
from clickhouse_connect.driver import AsyncClient, Client  # type: ignore[attr-defined]
from loguru import logger

from src.core.config import get_settings

settings = get_settings()


class ClickHousePool:
    def __init__(
        self,
        size: int,
        factory: Callable[[], Client],
        healthcheck_query: str = "SELECT 1",
        healthcheck_timeout: float = 2.0,
    ) -> None:
        self._pool: asyncio.Queue[AsyncClient] = asyncio.Queue(maxsize=size)
        self._factory = factory
        self._init_lock = asyncio.Lock()
        self._initialized = False

        self._healthcheck_query = healthcheck_query
        self._healthcheck_timeout = healthcheck_timeout

    async def _make_async_client(self) -> AsyncClient:
        base = await asyncio.to_thread(self._factory)
        return AsyncClient(client=base)

    async def _replace_client(self, client: AsyncClient) -> AsyncClient:
        # Закрываем старый (даже если он уже полумёртв)
        try:
            await client.close()  # type: ignore[no-untyped-call]
        except Exception as e:
            logger.debug("Error while closing bad ClickHouse client: {e}", e=str(e))

        # Создаём новый
        new_client = await self._make_async_client()
        logger.info(
            "Recreated ClickHouse client {old} -> {new}",
            old=str(client),
            new=str(new_client),
        )
        return new_client

    async def _healthcheck(self, client: AsyncClient) -> bool:
        """Проверяем, что соединение живое.

        Самый переносимый вариант — SELECT 1.
        """
        try:
            await asyncio.wait_for(
                client.query(self._healthcheck_query),
                timeout=self._healthcheck_timeout,
            )
            return True
        except Exception as e:
            logger.warning("ClickHouse client healthcheck failed: {e}", e=str(e))
            return False

    async def _initialize(self) -> None:
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            for _ in range(self._pool.maxsize):
                client = await self._make_async_client()
                await self._pool.put(client)
            self._initialized = True

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[AsyncClient]:
        await self._initialize()

        # опционально: таймаут ожидания свободного клиента
        # client = await asyncio.wait_for(self._pool.get(), timeout=10)
        client = await self._pool.get()
        try:
            if not await self._healthcheck(client):
                client = await self._replace_client(client)

            logger.debug("Acquiring clickhouse_session from {client}", client=str(client))
            yield client
        finally:
            # Возвращаем именно тот client, который реально использовался (в т.ч. пересозданный)
            try:
                self._pool.put_nowait(client)
            except asyncio.QueueFull:
                # На всякий случай, чтобы не потерять закрытие при логической ошибке
                logger.error("ClickHouse pool queue is full on release; closing client")
                try:
                    await client.close()  # type: ignore[no-untyped-call]
                except Exception:
                    logger.warning("Failed to close ClickHouse client on pool release")
            logger.debug("Put clickhouse_session {client}", client=str(client))

    async def close_all(self) -> None:
        """Дожидается возврата всех клиентов в пул и закрывает соединения."""
        if not self._initialized:
            return

        clients: list[AsyncClient] = []
        # Ждём, пока вернутся все экземпляры (их столько же, сколько размер пула)
        for _ in range(self._pool.maxsize):
            client = await self._pool.get()
            clients.append(client)

        # Закрываем соединения параллельно
        await asyncio.gather(*(client.close() for client in clients))  # type: ignore[no-untyped-call]
        self._initialized = False


def create_pool(size: int) -> ClickHousePool:
    return ClickHousePool(
        size,
        partial(
            get_client,
            host=settings.clickhouse_settings.HOST,
            port=settings.clickhouse_settings.PORT,
            username=settings.clickhouse_settings.USERNAME,
            password=settings.clickhouse_settings.PASSWORD,
            database=settings.clickhouse_settings.DATABASE,
        ),
    )
