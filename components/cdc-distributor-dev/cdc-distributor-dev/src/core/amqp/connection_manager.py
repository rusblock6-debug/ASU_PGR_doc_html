"""Менеджер AMQP-соединения для публикации в очереди бортов."""

from aio_pika import connect_robust
from aio_pika.abc import AbstractChannel, AbstractRobustConnection
from aio_pika.pool import Pool
from loguru import logger


class AMQPConnectionManager:
    """Управляет единственным AMQP-соединением и пулом каналов.

    Использует connect_robust() для автоматического переподключения
    при разрыве связи с брокером. Каналы создаются с publisher_confirms=True
    для гарантии доставки.

    Lifecycle:
        manager = AMQPConnectionManager(host=..., port=..., login=..., password=...)
        await manager.start()   # открывает соединение, инициализирует пул
        ...                     # использование через manager.channel_pool
        await manager.stop()    # закрывает пул и соединение
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        login: str,
        password: str,
        channel_pool_size: int = 10,
    ) -> None:
        self._host = host
        self._port = port
        self._login = login
        self._password = password
        self._pool_size = channel_pool_size
        self._connection: AbstractRobustConnection | None = None
        self._channel_pool: Pool[AbstractChannel] | None = None

    async def start(self) -> None:
        """Открывает AMQP-соединение и создаёт пул каналов."""
        logger.info(
            "Connecting to AMQP host={host} port={port}",
            host=self._host,
            port=self._port,
        )
        self._connection = await connect_robust(
            host=self._host,
            port=self._port,
            login=self._login,
            password=self._password,
        )
        self._channel_pool = Pool(
            self._get_channel,
            max_size=self._pool_size,
        )
        logger.info(
            "AMQP connection established, channel pool created pool_size={size}",
            size=self._pool_size,
        )

    async def _get_channel(self) -> AbstractChannel:
        """Factory для создания канала с publisher confirms."""
        if self._connection is None:
            raise RuntimeError("Connection not started")
        channel = await self._connection.channel(publisher_confirms=True)
        logger.debug("AMQP channel created with publisher_confirms=True")
        return channel

    async def stop(self) -> None:
        """Закрывает пул каналов и AMQP-соединение."""
        if self._channel_pool is not None:
            await self._channel_pool.close()
            logger.debug("Channel pool closed")
        if self._connection is not None:
            await self._connection.close()
            logger.info("AMQP connection closed")
        self._connection = None
        self._channel_pool = None

    @property
    def channel_pool(self) -> Pool[AbstractChannel]:
        """Пул каналов для публикации. Используется AMQPPublisher."""
        if self._channel_pool is None:
            raise RuntimeError("AMQPConnectionManager not started. Call start() first.")
        return self._channel_pool
