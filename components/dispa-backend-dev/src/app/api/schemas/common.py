"""Общие Pydantic схемы."""

from datetime import datetime

from pydantic import BaseModel, Field


class PaginatedResponse[T](BaseModel):
    """Пагинированный ответ для списков."""

    items: list[T] = Field(..., description="Элементы списка")
    total: int = Field(..., description="Общее количество элементов")
    page: int = Field(..., description="Текущая страница")
    size: int = Field(..., description="Размер страницы")
    pages: int = Field(..., description="Общее количество страниц")

    @classmethod
    def create(cls, items: list[T], total: int, page: int, size: int) -> "PaginatedResponse[T]":
        """Создать пагинированный ответ."""
        pages = (total + size - 1) // size if size > 0 else 0
        return cls(items=items, total=total, page=page, size=size, pages=pages)


class MessageResponse(BaseModel):
    """Ответ с сообщением."""

    message: str = Field(..., description="Сообщение")
    success: bool = Field(default=True, description="Статус успеха")


class ErrorResponse(BaseModel):
    """Ответ ошибки."""

    status_code: int = Field(..., description="HTTP статус код")
    detail: str = Field(..., description="Детали ошибки")
    error_type: str = Field(..., description="Тип ошибки")


class BulkResponse(BaseModel):
    """Ответы при множественной операции."""

    success: bool = Field(..., description="Статус операции")
    count: int = Field(..., description="Количество обработанных элементов")


class TimestampBase(BaseModel):
    """Базовая схема с временными метками."""

    created_at: datetime = Field(..., description="Время создания")
    updated_at: datetime = Field(..., description="Время обновления")
