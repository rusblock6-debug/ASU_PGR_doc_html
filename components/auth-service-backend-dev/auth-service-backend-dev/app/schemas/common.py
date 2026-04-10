from typing import TypeVar, Generic, List, Optional
from pydantic import BaseModel, Field, model_validator
import math


T = TypeVar('T')


class PaginationBase(BaseModel, Generic[T]):
    """Базовый класс пагинации"""

    total: int = Field(..., description="Общее количество событий")
    page: int = Field(..., ge=1, description="Номер страницы")
    pages: int = Field(default=0, description="Всего страниц")
    size: int = Field(..., ge=1, le=100, description="Размер страницы")
    items: List[T] = Field(..., description="Элементы на странице")

    @model_validator(mode='after')
    def compute_pages(self):
        """Вычисляем количество страниц после валидации"""
        self.pages = math.ceil(self.total / self.size) if self.total > 0 else 0
        return self

    class Config:
        from_attributes = True


class StrList(BaseModel):
    items: Optional[List[str]] = Field(default=None)
