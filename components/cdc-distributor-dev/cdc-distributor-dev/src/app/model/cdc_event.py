"""Модели CDC событий Debezium."""

from typing import Any

import msgspec


class SchemaField(msgspec.Struct):
    """Описание поля в Debezium schema."""

    field: str
    type: str
    optional: bool = False
    default: Any = None
    name: str = ""  # Debezium semantic type (e.g., "io.debezium.time.MicroTimestamp")
    version: int | None = None


class Schema(msgspec.Struct):
    """Debezium schema описание структуры события."""

    type: str
    fields: list[SchemaField]
    optional: bool = False
    name: str = ""


class Envelope(msgspec.Struct):
    """Конверт CDC события с schema и payload."""

    schema: Schema
    payload: dict[str, Any]
