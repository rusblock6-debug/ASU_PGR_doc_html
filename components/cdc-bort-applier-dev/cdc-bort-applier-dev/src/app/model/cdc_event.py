import msgspec
from typing import Any


class SchemaField(msgspec.Struct):
    field: str
    type: str
    optional: bool = False
    default: Any = None
    name: str = ""  # Debezium semantic type (e.g., "io.debezium.time.MicroTimestamp")
    version: int | None = None


class Schema(msgspec.Struct):
    type: str
    fields: list[SchemaField]
    optional: bool = False
    name: str = ""


class Envelope(msgspec.Struct):
    schema: Schema
    payload: dict[str, Any]
