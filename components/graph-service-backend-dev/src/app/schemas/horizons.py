"""Pydantic модели для graph-service"""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationBase, TimestampBase
from app.schemas.shafts import ShaftShort


class HorizonBase(BaseModel):
    """Базовая модель горизонта"""

    name: str = Field(..., description="Название горизонта")
    height: float = Field(..., description="Высота горизонта в метрах")
    color: str | None = Field(
        "#2196F3",
        description="HEX цвет для визуализации (#RRGGBB)",
        pattern=r"^#[0-9A-Fa-f]{6}$",
    )


class HorizonCreate(HorizonBase):
    """Модель для создания горизонта"""

    id: int | None = Field(
        None,
        description="ID горизонта (опционально, для синхронизации с сервером)",
    )
    shafts: list[int] | None = Field(None, description="ID шахт для привязки горизонта")


class HorizonUpdate(BaseModel):
    """Модель для обновления горизонта (все поля опциональны)"""

    name: str | None = Field(None, description="Название горизонта")
    height: float | None = Field(None, description="Высота горизонта в метрах")
    color: str | None = Field(None, description="HEX цвет для визуализации (#RRGGBB)")
    shafts: list[int] | None = Field(None, description="ID шахт для привязки (заменяет текущие)")


class HorizonResponse(TimestampBase, HorizonBase):
    """Полная модель горизонта с привязанными шахтами"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID горизонта")
    shafts: list[ShaftShort] = Field(
        default=[],
        description="Список шахт, к которым привязан горизонт",
    )
    color: str = Field(
        description="HEX цвет для визуализации (#RRGGBB)",
        pattern=r"^#[0-9A-Fa-f]{6}$",
    )


class HorizonListResponse(PaginationBase[HorizonResponse]):
    """Ответ списка горизонтов с пагинацией."""

    pass


class HorizonShort(BaseModel):
    """Краткая схема возвращающая горизонт (для вложения в другие схемы)"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID горизонта")
    name: str = Field(..., description="Название горизонта")


class HorizonGraphBulkUpsertClientEdge(BaseModel):
    """Схема данных ребер с клиента, для массового изменения графа дорог"""

    from_node_id: int | str = Field(..., description="ID ноды которую связывают с другой нодой")
    to_node_id: int | str = Field(..., description="ID ноды к которой привязывают другую ноду")


class HorizonGraphBulkUpsertServerEdge(BaseModel):
    """Схема данных ребер сохраненных в бд, для массового изменения графа дорог"""

    id: int = Field(..., description="ID ребра")
    from_node_id: int = Field(..., description="ID ноды которую связывают с другой нодой")
    to_node_id: int = Field(..., description="ID ноды к которой привязывают другую ноду")


class HorizonGraphBulkUpsertBaseNode(BaseModel):
    """Базовая схема нод, для массового изменения графа дорог"""

    x: float = Field(..., description="Координата по X")
    y: float = Field(..., description="Координата по Y")


class HorizonGraphBulkUpsertClientNode(HorizonGraphBulkUpsertBaseNode):
    """Схема данных ноды с клиента, для массового изменения графа дорог"""

    id: str = Field(..., description="ID ноды")


class HorizonGraphBulkUpsertServerNode(HorizonGraphBulkUpsertBaseNode):
    """Схема данных нод сохраненных в бд, для массового изменения графа дорог ()"""

    id: int = Field(..., description="ID ноды")


class HorizonGraphBulkUpsertRequest(BaseModel):
    """Входная схема данных для массового изменения графа дорог (ноды, ребра)"""

    nodes: list[HorizonGraphBulkUpsertClientNode | HorizonGraphBulkUpsertServerNode]
    edges: list[HorizonGraphBulkUpsertServerEdge | HorizonGraphBulkUpsertClientEdge]
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "nodes": [
                    {
                        "id": 348,
                        "x": 59.82921490888786,
                        "y": 58.16971791580272,
                    },
                    {
                        "id": "BlP70r9EgwWbVhL9gy4mP",
                        "x": 59.81611859110092,
                        "y": 58.16929578400393,
                    },
                ],
                "edges": [
                    {
                        "id": 317,
                        "from_node_id": 348,
                        "to_node_id": 338,
                    },
                    {
                        "from_node_id": 264,
                        "to_node_id": "BlP70r9EgwWbVhL9gy4mP",
                    },
                    {
                        "from_node_id": "BlP70r9EgwWbVhL9gy4mP",
                        "to_node_id": "aSgXmXYferbyZb24UHOrG",
                    },
                ],
            },
        },
    )
