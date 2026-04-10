"""Pydantic schemas для категорий видов грузов."""

from pydantic import BaseModel, Field

from .base import APIBaseModel


class APICreateLoadTypeCategories(APIBaseModel):
    """Схема создания категории вида груза."""

    name: str = Field(..., description="Наименование категории вида груза")
    is_mineral: bool = Field(False, description="Является ли данная категория полезным ископаемым")


class APIUpdateLoadTypeCategories(APICreateLoadTypeCategories):
    """Схема обновления категории вида груза."""


class APIResponseLoadTypeCategoryModel(APICreateLoadTypeCategories):
    """Модель ответа категории вида груза."""

    id: int


class APIResponseLoadTypeCategoriesModel(BaseModel):
    """Модель ответа списка категорий видов грузов."""

    page: int = 1
    pages: int
    size: int = 10
    total: int
    items: list[APIResponseLoadTypeCategoryModel] = Field(
        ...,
        description="Список категорий видов грузов",
    )
