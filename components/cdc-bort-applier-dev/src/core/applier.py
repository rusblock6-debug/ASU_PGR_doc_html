import abc

import msgspec

from .aggregator import AggregatedBatch


class ApplyResult(msgspec.Struct, frozen=True):
    """Результат применения batch."""

    upserted: int
    deleted: int


class Applier[T](abc.ABC):
    """
    Базовый класс для применения агрегированного batch в целевой data source.

    T - тип записи в batch (обычно dict или dataclass)
    """

    @abc.abstractmethod
    async def apply(self, batch: AggregatedBatch[T]) -> ApplyResult:
        """Применяет batch к целевому источнику."""
        ...
