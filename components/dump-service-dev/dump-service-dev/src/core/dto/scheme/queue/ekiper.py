"""Схемы очередей для обработки событий Ekiper."""

import dataclasses
from pathlib import Path
from typing import Any

import pyarrow as pa
from pydantic import BaseModel


@dataclasses.dataclass
class EkiperEvent:
    """Event enqueued for async parquet dumping."""

    filename: str
    row: dict[str, Any]
    topic: str
    schema: pa.Schema | None = None
    schema_model: type[BaseModel] | None = None


@dataclasses.dataclass
class EkiperSaveFile:
    """Dump file generated."""

    filepath: Path
