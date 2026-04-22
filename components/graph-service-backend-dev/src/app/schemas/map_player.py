import datetime
from enum import StrEnum

from pydantic import AliasChoices, BaseModel, Field


class PlaybackStatus(StrEnum):
    READY = "ready"
    PROCESSING = "processing"
    ERROR = "error"


class Playback(BaseModel):
    start_date: datetime.datetime
    end_date: datetime.datetime

    vehicle_ids: list[int]


class VehicleTelemetryItem(BaseModel):
    vehicle_id: int = Field(validation_alias=AliasChoices("bort", "vehicle_id"))
    timestamp: datetime.datetime
    lat: float
    lon: float
    height: float | None = None
    speed: float | None = None
    fuel: float | None = None


class PlaybackCacheEntry(BaseModel):
    status: PlaybackStatus = Field(description="Текущий статус генерации чанков")
    chunk_count: int = Field(description="Количество уже сгенерированных чанков")
    total_chunk_counts: int = Field(default=0, description="Ожидаемое общее количество чанков")
    chunk_duration: int = Field(default=0, description="Длительность одного чанка в секундах")
    created_at: str = Field(description="Дата создания записи в формате ISO 8601")
    start_date: str = Field(description="Дата начала воспроизведения в формате ISO 8601")
    end_date: str = Field(description="Дата окончания воспроизведения в формате ISO 8601")
    vehicle_ids: str = Field(...)


class PlaybackManifest(BaseModel):
    hash: str = Field(description="Уникальный хэш воспроизведения")
    status: PlaybackStatus = Field(description="Текущий статус генерации чанков")
    chunk_count: int = Field(description="Количество уже сгенерированных чанков")
    total_chunk_counts: int = Field(default=0, description="Ожидаемое общее количество чанков")
    chunk_duration_sec: int = Field(description="Длительность одного чанка в секундах")
    start_date: datetime.datetime = Field(description="Дата начала воспроизведения")
    end_date: datetime.datetime = Field(description="Дата окончания воспроизведения")
    vehicle_ids: list[int] = Field(...)


class PlaybackChunkResponse(BaseModel):
    hash: str
    chunk_index: int
    total_chunks: int
    data: list[VehicleTelemetryItem]
