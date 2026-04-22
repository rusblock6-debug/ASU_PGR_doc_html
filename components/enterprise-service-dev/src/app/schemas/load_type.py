"""Pydantic schemas для видов грузов."""

from pydantic import BaseModel, Field

from app.schemas.base import APIBaseModel
from app.schemas.load_type_categories import APIResponseLoadTypeCategoryModel


class APICreateLoadType(APIBaseModel):
    """Схема создания вида груза."""

    name: str = Field(..., description="Наименование вида груза")
    density: float = Field(..., description="Плотность вида груза")
    color: str = Field(..., description="Цвет вида груза")
    category_id: int = Field(..., description="Id категории вида груза")


class APIUpdateLoadType(APICreateLoadType):
    """Схема обновления вида груза."""


class APILoadTypeResponseModel(APICreateLoadType):
    """Модель ответа вида груза."""

    id: int
    category: APIResponseLoadTypeCategoryModel | None


class APILoadTypesResponseModel(BaseModel):
    """Модель ответа списка видов грузов."""

    page: int = 1
    pages: int
    size: int = 10
    total: int
    items: list[APILoadTypeResponseModel] = Field(..., description="Список видов грузов")
