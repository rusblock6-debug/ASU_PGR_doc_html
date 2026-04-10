# ruff: noqa: D100, D101
from pydantic import BaseModel, ConfigDict, Field

from src.app.type import SyncStatus


class File(BaseModel):
    id: int = Field(...)
    path: str = Field(..., description="Путь до архива")
    sync_status: SyncStatus = Field(..., description="Статус синхронизация на s3")

    model_config = ConfigDict(from_attributes=True)
