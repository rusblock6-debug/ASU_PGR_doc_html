"""Middleware для повторной обработки с экспоненциальной задержкой."""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from faststream._internal.middlewares import BaseMiddleware

from app.core.config import settings

if TYPE_CHECKING:
    from faststream._internal.basic_types import AsyncFuncAny
    from faststream._internal.context.repository import ContextRepo
    from faststream.message import StreamMessage

logger = logging.getLogger("Retry middleware")


def _retry_middleware_factory(
    max_attempts: int = settings.rabbit.retry_max_attempts,
    base_delay_sec: float = settings.rabbit.retry_base_delay_sec,
) -> Any:
    """Фабрика BrokerMiddleware: повтор обработки с экспоненциальной задержкой."""

    class RetryMiddleware(BaseMiddleware[Any, Any]):
        async def consume_scope(
            self,
            call_next: "AsyncFuncAny",
            msg: "StreamMessage[Any]",
        ) -> Any:
            last_exc: BaseException | None = None
            for attempt in range(max_attempts):
                try:
                    return await call_next(msg)
                except BaseException as e:
                    last_exc = e
                    if attempt == max_attempts - 1:
                        raise
                    delay = base_delay_sec * (2**attempt)
                    logger.warning(
                        "Retry attempt %s/%s after %.2fs: %s",
                        attempt + 1,
                        max_attempts,
                        delay,
                        e,
                        exc_info=True,
                    )
                    await asyncio.sleep(delay)
            if last_exc is not None:
                raise last_exc
            return None

    def middleware(
        msg: Any,
        *,
        context: "ContextRepo",
    ) -> RetryMiddleware:
        return RetryMiddleware(msg, context=context)

    return middleware


RetryExponentialBackoffMiddleware = _retry_middleware_factory()
