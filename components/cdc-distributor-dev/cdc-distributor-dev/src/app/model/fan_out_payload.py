"""Модель JSON-сообщения для публикации в очереди бортов."""

from typing import Any

import msgspec


class TableBatch(msgspec.Struct, frozen=True):
    """Upserts и deletes для одной таблицы в агрегате."""

    upserts: list[dict[str, Any]]
    deletes: list[dict[str, Any]]


class FanOutPayload(msgspec.Struct, frozen=True):
    """JSON payload публикуемый в очередь борта.

    Содержит агрегированные изменения по таблицам и метаданные для
    восстановления порядка на стороне applier-а.
    """

    seq_id: int  # последовательный номер агрегата для упорядочивания
    low_offset: int  # минимальный offset стрима, схлопнутый в этот агрегат
    up_offset: int  # максимальный offset стрима, схлопнутый в этот агрегат
    tables: dict[str, TableBatch]  # upserts/deletes по таблицам
