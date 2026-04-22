"""StreamApp — приложение для обработки стримов через rstream Consumer."""

from __future__ import annotations

import asyncio
import contextvars
from collections.abc import AsyncGenerator, Callable, Coroutine
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from loguru import logger
from rstream import Consumer, ConsumerOffsetSpecification, MessageContext, OffsetType

from .router import BatchMetadata, StreamRouter

LifespanState = dict[str, Any] | Any  # Поддержка dict или любого объекта
Lifespan = Callable[["StreamApp"], AbstractAsyncContextManager[LifespanState]]

# Context variable для текущего StreamApp
_current_app: contextvars.ContextVar[StreamApp | None] = contextvars.ContextVar(
    "current_app",
    default=None,
)


def get_current_app() -> StreamApp:
    """Get current StreamApp from context.

    Used for DI in handlers to access app's state (factory).

    Returns:
        Current StreamApp instance

    Raises:
        RuntimeError: If no active StreamApp in context
    """
    app = _current_app.get()
    if app is None:
        raise RuntimeError("No active StreamApp in context")
    return app


class BortOffsetAdapter:
    """Адаптер BortOffsetManager для использования в StreamApp.

    StreamApp.start() вызывает offset_manager.get_offset(stream_name).
    Этот адаптер подставляет фиксированный bort_id из контекста consumer'а.
    """

    def __init__(self, bort_offset_manager: Any, bort_id: int) -> None:
        self._bort_offset_manager = bort_offset_manager
        self._bort_id = bort_id

    async def get_offset(self, stream_name: str) -> int | None:
        """Получить offset для стрима и борта."""
        return await self._bort_offset_manager.get_offset(stream_name, self._bort_id)

    async def initialize_table(self) -> None:
        """Инициализация таблицы (no-op, выполняется в __main__.py)."""


@asynccontextmanager
async def default_lifespan(app: StreamApp) -> AsyncGenerator[LifespanState]:
    """Default lifespan that does nothing."""
    yield {}


def make_bort_lifespan(
    *,
    factory: Any,
    offset_adapter: Any,
) -> Lifespan:
    """Создает lifespan для per-bort consumer.

    Yields factory as state. Attaches _offset_adapter for StreamApp.start()
    offset loading via duck-type check.

    Args:
        factory: ServiceFactory subclass с фиксированным bort_id
        offset_adapter: BortOffsetAdapter для загрузки per-bort offset
    """

    @asynccontextmanager
    async def _bort_lifespan(app: StreamApp) -> AsyncGenerator[Any]:
        # Attach offset adapter to factory for StreamApp.start() offset loading
        factory._offset_adapter = offset_adapter
        logger.info("Starting bort consumer lifespan")
        yield factory
        logger.info("Bort consumer lifespan stopped")

    return _bort_lifespan


@dataclass(slots=True)
class EnrichedEvent[T]:
    """Event enriched with stream offset."""

    offset: int
    event: T


@dataclass(slots=True)
class StreamBuffer:
    """Буфер для накопления сообщений стрима."""

    events: list[EnrichedEvent[Any]] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    flush_task: asyncio.Task[None] | None = None


class StreamApp:
    """Приложение для обработки стримов через rstream Consumer.

    Использует роутер для определения хэндлеров и их конфигурации.
    Каждый стрим использует свой decoder из конфига роутера.
    Поддерживает батчинг с учётом batch_size и timeout.
    """

    def __init__(
        self,
        router: StreamRouter,
        *,
        name: str = "",
        lifespan: Lifespan | None = None,
        host: str = "localhost",
        port: int = 5552,
        vhost: str = "/",
        username: str = "guest",
        password: str = "guest",  # noqa: S107
    ) -> None:
        self._router = router
        self._name = name
        self._lifespan = lifespan or default_lifespan
        self._lifespan_cm: AbstractAsyncContextManager[LifespanState] | None = None
        self.state: LifespanState = {}
        self._host = host
        self._port = port
        self._vhost = vhost
        self._username = username
        self._password = password
        self._consumer: Consumer | None = None
        self._buffers: dict[str, StreamBuffer] = {}
        self._running = False

    @property
    def router(self) -> StreamRouter:
        """Доступ к роутеру для lifespan (чтение applier_metas)."""
        return self._router

    async def start(self) -> None:
        """Запускает consumer и подписывается на все зарегистрированные стримы."""
        logger.info(
            "Starting StreamApp host={host} port={port}",
            host=self._host,
            port=self._port,
        )

        self._lifespan_cm = self._lifespan(self)
        self.state = await self._lifespan_cm.__aenter__()
        logger.info("Lifespan started")

        self._consumer = Consumer(
            host=self._host,
            port=self._port,
            vhost=self._vhost,
            username=self._username,
            password=self._password,
            load_balancer_mode=True,
        )

        await self._consumer.start()
        self._running = True
        logger.info("Consumer started")

        streams = [config.name for config in self._router.all()]
        logger.info(
            "Registering streams={streams} count={count}",
            streams=streams,
            count=len(streams),
        )

        # Get offset_manager from state (BortConsumer path via BortOffsetAdapter)
        offset_manager = None
        if hasattr(self.state, "_offset_adapter"):
            offset_manager = self.state._offset_adapter
            logger.debug("Got offset_manager via _offset_adapter")
        else:
            logger.warning(f"No offset_manager in state type={type(self.state)}")

        for config in self._router.all():
            self._buffers[config.name] = StreamBuffer()

            # Загружаем последний offset для стрима
            last_offset = None
            if offset_manager:
                last_offset = await offset_manager.get_offset(config.name)

            # Создаём offset specification
            if last_offset is not None:
                offset_spec = ConsumerOffsetSpecification(
                    OffsetType.OFFSET,
                    last_offset + 1,  # Начинаем со следующего offset
                )
                logger.info(
                    "Resuming from offset stream={stream} offset={offset}",
                    stream=config.name,
                    offset=last_offset + 1,
                )
            else:
                offset_spec = ConsumerOffsetSpecification(OffsetType.FIRST)
                logger.info(
                    "Starting from beginning stream={stream}",
                    stream=config.name,
                )

            callback = self._make_callback(config.name)
            await self._consumer.subscribe(
                stream=config.name,
                callback=callback,
                offset_specification=offset_spec,
                subscriber_name=f"{self._name}:{config.name}" if self._name else config.name,
            )
            logger.info(
                "Subscribed stream={stream} batch_size={batch_size} timeout={timeout}",
                stream=config.name,
                batch_size=config.batch_size,
                timeout=config.timeout,
            )

    async def run(self) -> None:
        """Запускает основной цикл обработки."""
        if self._consumer is None:
            raise RuntimeError("Consumer not started. Call start() first.")
        await self._consumer.run()

    async def stop(self) -> None:
        """Останавливает consumer и флашит все буферы."""
        logger.info("Stopping StreamApp")
        self._running = False

        for stream_name in self._buffers:
            await self._flush_buffer(stream_name)

        if self._consumer:
            await self._consumer.close()
            self._consumer = None

        if self._lifespan_cm:
            await self._lifespan_cm.__aexit__(None, None, None)
            logger.info("Lifespan stopped")

        logger.info("StreamApp stopped")

    @staticmethod
    def _strip_amqp_header(body: bytes) -> bytes:
        """Удаляет AMQP 1.0 header из сообщения."""
        if body.startswith(b"\x00Su\xb0"):
            return body[8:]
        if not body.startswith(b"{"):
            idx = body.find(b"{")
            if idx != -1:
                return body[idx:]
        return body

    def _make_callback(
        self,
        stream_name: str,
    ) -> Callable[..., Coroutine[Any, Any, None]]:
        """Создаёт callback для конкретного стрима."""
        config = self._router.get(stream_name)
        decoder = config.decoder

        async def on_message(body: bytes, ctx: MessageContext) -> None:
            logger.debug("Message received stream={stream}", stream=stream_name)

            if not self._running:
                return

            try:
                buffer = self._buffers[stream_name]

                if isinstance(body, memoryview):
                    body = bytes(body)

                body = self._strip_amqp_header(body)
                event = decoder.decode(body)

                # Обогащаем событие offset'ом
                enriched_event = EnrichedEvent(
                    offset=ctx.offset,
                    event=event,
                )
                need_flush = False
                async with buffer.lock:
                    buffer.events.append(enriched_event)

                    if len(buffer.events) >= config.batch_size:
                        need_flush = True
                    elif buffer.flush_task is None or buffer.flush_task.done():
                        buffer.flush_task = asyncio.create_task(
                            self._schedule_flush(stream_name, config.timeout),
                        )
                if need_flush:
                    await self._flush_buffer(stream_name)
            except Exception:
                logger.exception(
                    "Error processing message stream={stream}",
                    stream=stream_name,
                )

        return on_message

    async def _schedule_flush(self, stream_name: str, timeout: float) -> None:
        """Планирует flush буфера по таймауту."""
        await asyncio.sleep(timeout)
        await self._flush_buffer(stream_name)

    async def _flush_buffer(self, stream_name: str) -> None:
        """Флашит буфер и вызывает хэндлер."""
        buffer = self._buffers[stream_name]

        async with buffer.lock:
            if not buffer.events:
                return

            enriched_events = buffer.events
            buffer.events = []

            if buffer.flush_task and not buffer.flush_task.done():
                buffer.flush_task.cancel()
                try:
                    await buffer.flush_task
                except asyncio.CancelledError:
                    pass
            buffer.flush_task = None

        # Извлекаем события и вычисляем max_offset и min_offset
        events = [e.event for e in enriched_events]
        max_offset = max(e.offset for e in enriched_events)
        min_offset = min(e.offset for e in enriched_events)

        # Создаём метаданные batch
        batch_metadata = BatchMetadata(
            stream_name=stream_name,
            max_offset=max_offset,
            min_offset=min_offset,
        )

        config = self._router.get(stream_name)
        logger.debug(
            "Flushing buffer stream={stream} events={events} max_offset={offset}",
            stream=stream_name,
            events=len(events),
            offset=max_offset,
        )

        token = _current_app.set(self)
        try:
            await config.handler(events, batch_metadata)
        finally:
            _current_app.reset(token)
