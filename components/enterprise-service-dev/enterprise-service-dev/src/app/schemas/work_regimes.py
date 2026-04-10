"""Pydantic schemas для Work Regimes."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import PaginationBase


class ShiftDefinition(BaseModel):
    """Определение смен в режиме работы.

    Время хранится в секундах от начала суток (00:00).
    """

    shift_num: int = Field(..., ge=1, description="Номер смены (1, 2, 3, etc.)")
    start_time_offset: int = Field(
        ...,
        ge=-86400,
        le=86399,
        description=(
            "Время начала смены в секундах от 00:00"
            " (может быть отрицательным для смен,"
            " начинающихся в предыдущий день)"
        ),
    )
    end_time_offset: int = Field(
        ...,
        ge=0,
        le=86399,
        description="Время окончания смены в секундах от 00:00",
    )

    class Config:
        """Конфигурация Pydantic модели."""

        from_attributes = True


class WorkRegimeBase(BaseModel):
    """Базовая схема режима работы."""

    enterprise_id: int = Field(..., description="ID предприятия")
    name: str = Field(..., min_length=1, max_length=100, description="Название режима")
    description: str | None = Field(None, description="Описание режима")
    shifts_definition: list[ShiftDefinition] = Field(..., description="Определение смен")
    is_active: bool = Field(default=True, description="Режим активен")


class WorkRegimeCreate(BaseModel):
    """Схема создания режима работы."""

    enterprise_id: int = Field(..., description="ID предприятия")
    name: str = Field(..., min_length=1, max_length=100, description="Название режима")
    description: str | None = Field(None, description="Описание режима")
    shifts_definition: list[ShiftDefinition] = Field(..., description="Определение смен")


class WorkRegimeUpdate(BaseModel):
    """Схема обновления режима работы."""

    name: str | None = None
    description: str | None = None
    shifts_definition: list[ShiftDefinition] | None = None
    is_active: bool | None = None


class WorkRegimeResponse(WorkRegimeBase):
    """Ответ режима работы."""

    id: int = Field(..., description="ID режима работы")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: datetime = Field(..., description="Время обновления")

    class Config:
        """Конфигурация Pydantic модели."""

        from_attributes = True


class WorkRegimeListResponse(PaginationBase[WorkRegimeResponse]):
    """Ответ списка режимов работы с пагинацией."""
