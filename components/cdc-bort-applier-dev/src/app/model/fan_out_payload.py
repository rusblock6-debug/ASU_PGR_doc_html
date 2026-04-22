"""Доменные модели для FanOutPayload от cdc-distributor."""

from typing import Any

import msgspec


class TableBatch(msgspec.Struct, frozen=True):
    """Batch изменений для одной таблицы."""

    upserts: list[dict[str, Any]]
    deletes: list[Any]


class FanOutPayloadMsg(msgspec.Struct, frozen=True):
    """FanOutPayload агрегат от cdc-distributor.

    Содержит все изменения для одного CDC-цикла.
    seq_id используется для дедупликации и проверки порядка.
    """

    seq_id: int
    low_offset: int
    up_offset: int
    tables: dict[str, TableBatch]
