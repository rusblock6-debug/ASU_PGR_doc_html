"""Pydantic модели для graph-service"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import TimestampBase


class EdgeBase(BaseModel):
    """Базовая модель ребра графа"""

    from_node_id: int = Field(..., description="ID начального узла")
    to_node_id: int = Field(..., description="ID конечного узла")
    edge_type: str = Field(default="horizontal", description="Тип ребра: horizontal или vertical")
    direction: Literal["Двунаправленное", "Одностороннее"] = Field(
        default="Двунаправленное",
        description="Направление дороги: Двунаправленное или Одностороннее",
    )


class EdgeCreate(EdgeBase):
    """Модель для создания ребра графа"""

    horizon_id: int | None = Field(None, description="ID горизонта (None для межгоризонтных)")
    id: int | None = Field(
        None,
        description="ID ребра (опционально, для синхронизации с сервером)",
    )


class EdgeResponse(TimestampBase, EdgeBase):
    """Полная модель ребра графа"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID ребра")
    horizon_id: int | None = Field(None, description="ID горизонта")


class EdgeSplitRequest(BaseModel):
    """Запрос на разрезание ребра точкой."""

    x: float = Field(..., description="Координата X новой точки")
    y: float = Field(..., description="Координата Y новой точки")
    node_type: str = Field(default="junction", description="Тип создаваемого узла")
    node_id: int | None = Field(None, description="ID узла (опционально, для синхронизации)")


class EdgeBatchUpdateItem(BaseModel):
    id: int = Field(..., description="ID ребра")
    from_node_id: int | None = Field(None, description="ID начального узла")
    to_node_id: int | None = Field(None, description="ID конечного узла")
    edge_type: str | None = Field(None, description="Тип ребра")
    direction: Literal["Двунаправленное", "Одностороннее"] | None = Field(
        None,
        description="Направление дороги",
    )


class EdgeBatchUpdateRequest(BaseModel):
    items: list[EdgeBatchUpdateItem] = Field(
        ...,
        min_length=1,
        description="Список обновляемых рёбер",
    )


class EdgeBatchDeleteRequest(BaseModel):
    ids: list[int] = Field(..., min_length=1, description="Список ID рёбер для удаления")
