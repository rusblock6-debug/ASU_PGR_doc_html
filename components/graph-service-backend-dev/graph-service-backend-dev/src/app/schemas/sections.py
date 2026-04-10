"""Pydantic schemas для моделей участков."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationBase, TimestampBase
from app.schemas.horizons import HorizonShort


class SectionBase(BaseModel):
    """Общие поля для всех схем"""

    name: str = Field(..., max_length=100, min_length=1, description="Название участков")
    is_contractor_organization: bool | None = Field(
        description="Является ли участок контрактной организацией",
    )
    horizons: list[int] | None = Field(description="Список ID горизонтов")


class SectionCreate(SectionBase):
    """Схема для создания одного участка"""

    id: int | None = Field(
        None,
        description="ID участков (опционально, для синхронизации с сервером)",
    )


class SectionUpdate(SectionBase):
    """Схема для обновления одного участка"""

    name: str | None = Field(max_length=100, min_length=1, description="Название участков")  # type: ignore[assignment]


class SectionBulkUpdate(SectionBase):
    """Схема для обновления множества участков"""

    id: int = Field(..., description="ID участка для обновления")
    name: str | None = Field(max_length=100, min_length=1, description="Название участков")  # type: ignore[assignment]


class SectionResponse(TimestampBase, SectionBase):
    """Ответ возвращающий участок."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID шахты")
    horizons: list[HorizonShort] = Field(..., description="Список горизонтов")  # type: ignore[assignment]


class SectionListResponse(PaginationBase[SectionResponse]):
    """Ответ список шахт с пагинацией."""


class SectionListBulkCreate(BaseModel):
    """Запрос на bulk создание шахт"""

    items: list[SectionCreate] = Field(
        ...,
        min_length=1,
        description="Список участков для создания",
    )


class SectionListBulkUpdate(BaseModel):
    """Запрос на bulk обновление шахт"""

    items: list[SectionBulkUpdate] = Field(
        ...,
        min_length=1,
        description="Список участков для обновления",
    )
