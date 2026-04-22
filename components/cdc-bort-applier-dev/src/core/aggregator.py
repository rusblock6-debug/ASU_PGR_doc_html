import abc
from typing import Any, Protocol

import msgspec


class Codec[T](Protocol):
    def decode_event(self, raw: bytes) -> T: ...


class HasPayload(Protocol):
    payload: dict[str, Any]


class AggregatedBatch[T](msgspec.Struct, frozen=True):
    """Результат агрегации batch событий."""

    upserts: list[T]
    deletes: list[Any]


class EventAggregator[E: HasPayload, T](abc.ABC):
    """
    Базовый агрегатор для событий с payload.

    E - тип события (должен иметь payload)
    T - тип записи в результате (обычно dict или dataclass)
    """

    @abc.abstractmethod
    def aggregate(self, events: list[E]) -> AggregatedBatch[T]:
        """Агрегирует список событий."""
        ...
