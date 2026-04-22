"""Общие Pydantic schemas для всех сущностей."""

import math
from datetime import datetime
from typing import TypeVar

from pydantic import BaseModel, Field, model_validator

T = TypeVar("T")


class TimestampBase(BaseModel):
    """Базовая схема с временными метками."""

    created_at: datetime = Field(..., description="Время создания")
    updated_at: datetime = Field(..., description="Время обновления")


class PaginationBase[T](BaseModel):
    """Базовый класс пагинации"""

    total: int = Field(..., description="Общее количество событий")
    page: int = Field(..., ge=1, description="Номер страницы")
    pages: int = Field(default=0, description="Всего страниц")
    size: int = Field(..., ge=1, le=100, description="Размер страницы")
    items: list[T] = Field(..., description="Элементы на странице")

    @model_validator(mode="after")
    def compute_pages(self):
        """Вычисляем количество страниц после валидации"""
        self.pages = math.ceil(self.total / self.size) if self.total > 0 else 0
        return self

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Ответ ошибки."""

    status_code: int = Field(..., description="HTTP статус код")
    detail: str = Field(..., description="Детали ошибки")
    error_type: str = Field(..., description="Тип ошибки")
