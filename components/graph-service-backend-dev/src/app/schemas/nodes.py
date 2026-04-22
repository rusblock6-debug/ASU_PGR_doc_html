"""Pydantic модели для graph-service"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import TimestampBase


class NodeBase(BaseModel):
    """Базовая модель узла графа"""

    x: float = Field(..., description="Координата X")
    y: float = Field(..., description="Координата Y")
    z: float | None = Field(
        None,
        description="Координата Z: для ladder обязательна, иначе из horizon.height",
    )

    node_type: str = Field(default="road", description="Тип узла: road, junction, ladder")
    linked_nodes: str | None = Field(
        None,
        description="JSON строка со связанными узлами для ladder",
    )
    ladders_ids: list[int] | None = Field(
        None,
        description="ID всех связанных лестниц (обязательно для node_type=ladder)",
    )


class NodeCreate(NodeBase):
    """Модель для создания узла графа"""

    horizon_id: int = Field(..., description="ID горизонта")
    id: int | None = Field(
        None,
        description="ID узла (опционально, для синхронизации с сервером)",
    )

    @model_validator(mode="after")
    def validate_ladder_z(self):
        if self.node_type == "ladder" and self.z is None:
            raise ValueError("Field 'z' is required when node_type is 'ladder'")
        if self.node_type == "ladder" and not self.ladders_ids:
            raise ValueError("Field 'ladders_ids' is required when node_type is 'ladder'")
        return self


class NodeResponse(TimestampBase, NodeBase):
    """Полная модель узла графа"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID узла")
    horizon_id: int = Field(..., description="ID горизонта")


class NodePlaceLinksUpdate(BaseModel):
    place_ids: list[int] = Field(
        default_factory=list,
        description="Полный список place_id, связанных с вершиной дороги",
    )
