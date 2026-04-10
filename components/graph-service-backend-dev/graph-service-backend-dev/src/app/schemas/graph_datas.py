"""Pydantic модели для graph-service"""

from pydantic import BaseModel, Field

from app.schemas.edges import EdgeResponse
from app.schemas.horizons import HorizonResponse
from app.schemas.ladders import LadderResponse
from app.schemas.nodes import NodeResponse
from app.schemas.places import PlaceResponse
from app.schemas.tags import APITagResponseModel


class GraphData(BaseModel):
    """Данные графа для горизонта"""

    horizon: HorizonResponse = Field(..., description="Информация о горизонте")
    nodes: list[NodeResponse] = Field(..., description="Узлы графа")
    edges: list[EdgeResponse] = Field(..., description="Ребра графа")
    tags: list[APITagResponseModel] = Field(..., description="Метки на горизонте")
    places: list[PlaceResponse] = Field(
        default_factory=list,
        description="Места на горизонте",
    )
    node_places: list[dict] = Field(
        default_factory=list,
        description="Привязки мест к вершинам дороги в формате {'node_id': int, 'place_id': int}",
    )
    ladders: list[LadderResponse] = Field(
        default_factory=list,
        description="Лестницы, связанные с текущим горизонтом",
    )
