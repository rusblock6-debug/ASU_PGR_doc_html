"""Pydantic schemas для моделей шахты."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationBase, TimestampBase


class ShaftBase(BaseModel):
    """Общие поля для всех схем"""

    name: str = Field(..., max_length=100, min_length=1, description="Название шахты")


class ShaftCreate(ShaftBase):
    """Создание - name обязательно"""

    id: int | None = Field(
        None,
        description="ID шахты (опционально, для синхронизации с сервером)",
    )


class ShaftUpdateSingle(ShaftBase):
    """Обновление одной шахты (id из path параметра)"""

    pass


class ShaftUpdateBulk(ShaftBase):
    """Обновление шахты (для bulk операций id обязателен)"""

    id: int = Field(..., description="ID шахты для обновления")


class ShaftShort(ShaftBase):
    """Краткая схема возвращающая шахту (для вложения в другие схемы)"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID шахты")


class ShaftResponse(TimestampBase, ShaftBase):
    """Ответ возвращающий шахту."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID шахты")


class ShaftListResponse(PaginationBase[ShaftResponse]):
    """Ответ список шахт с пагинацией."""


class ShaftBulkCreateRequest(BaseModel):
    """Запрос на bulk создание шахт"""

    items: list[ShaftCreate] = Field(..., min_length=1, description="Список шахт для создания")


class ShaftBulkUpdateRequest(BaseModel):
    """Запрос на bulk обновление шахт"""

    items: list[ShaftUpdateBulk] = Field(
        ...,
        min_length=1,
        description="Список шахт для обновления",
    )
