"""Simple router to register MQTT subscriptions and associated handlers."""

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

Handler = Callable[..., Any | Awaitable[Any]]
HandlerT = TypeVar("HandlerT", bound=Handler)


@dataclass(frozen=True)
class Subscription:
    """Description of a single MQTT subscription handler."""

    topic: str
    qos: int
    handler: Handler
    name: str | None = None
    is_async: bool = False


class MQTTRouter:
    """Collect and manage MQTT subscriptions with optional prefixing."""

    def __init__(self, *, prefix: str = "") -> None:
        self.prefix = prefix.rstrip("/")
        self._subs: list[Subscription] = []

    @property
    def subscriptions(self) -> list[Subscription]:
        """Return a copy of registered subscriptions."""
        return list(self._subs)

    def include_router(self, router: "MQTTRouter") -> None:
        """Extend current router with subscriptions from another router."""
        for sub in router.subscriptions:
            topic = self._join(self.prefix, sub.topic)
            self._subs.append(
                Subscription(
                    topic=topic,
                    qos=sub.qos,
                    handler=sub.handler,
                    name=sub.name,
                    is_async=sub.is_async,
                ),
            )

    def subscriber(
        self,
        topic: str,
        *,
        qos: int = 1,
        name: str | None = None,
    ) -> Callable[[HandlerT], HandlerT]:
        """Decorator registering ``fn`` for the provided topic filter."""
        full_topic = self._join(self.prefix, topic)

        def decorator(fn: HandlerT) -> HandlerT:
            is_async = inspect.iscoroutinefunction(fn)
            self._subs.append(
                Subscription(topic=full_topic, qos=qos, handler=fn, name=name, is_async=is_async),
            )
            return fn

        return decorator

    @staticmethod
    def _join(prefix: str, topic: str) -> str:
        topic = topic.lstrip("/")
        if not prefix:
            return topic
        return f"{prefix}/{topic}"
