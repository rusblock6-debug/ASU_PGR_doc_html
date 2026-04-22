"""Pydantic schemas для Statuses."""

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.enums.statuses import AnalyticCategoryEnum
from app.schemas.common import PaginationBase


def transliterate(text: str) -> str:
    """Транслитерирует кириллицу в латиницу для генерации system_name."""
    translit_table = {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "yo",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
        "А": "A",
        "Б": "B",
        "В": "V",
        "Г": "G",
        "Д": "D",
        "Е": "E",
        "Ё": "YO",
        "Ж": "ZH",
        "З": "Z",
        "И": "I",
        "Й": "Y",
        "К": "K",
        "Л": "L",
        "М": "M",
        "Н": "N",
        "О": "O",
        "П": "P",
        "Р": "R",
        "С": "S",
        "Т": "T",
        "У": "U",
        "Ф": "F",
        "Х": "H",
        "Ц": "TS",
        "Ч": "CH",
        "Ш": "SH",
        "Щ": "SCH",
        "Ъ": "",
        "Ы": "Y",
        "Ь": "",
        "Э": "E",
        "Ю": "YU",
        "Я": "YA",
    }
    result = "".join(translit_table.get(char, char) for char in text)
    result = re.sub(r"[^a-zA-Z0-9]", "_", result)
    result = re.sub(r"_+", "_", result)
    result = result.strip("_")
    return result.lower()


class OrganizationCategoryBase(BaseModel):
    """Базовая схема организационной категории."""

    name: str = Field(..., min_length=1, max_length=100, description="Название категории")


class OrganizationCategoryCreate(OrganizationCategoryBase):
    """Схема создания организационной категории."""

    pass


class OrganizationCategoryUpdate(BaseModel):
    """Схема обновления организационной категории."""

    name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Название категории",
    )


class OrganizationCategoryResponse(OrganizationCategoryBase):
    """Ответ организационной категории."""

    id: int = Field(..., description="ID категории")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: datetime = Field(..., description="Время обновления")

    class Config:
        """Конфигурация Pydantic модели."""

        from_attributes = True


class OrganizationCategoryListResponse(PaginationBase[OrganizationCategoryResponse]):
    """Ответ списка организационных категорий с пагинацией."""

    pass


class StatusBase(BaseModel):
    """Базовая схема статуса."""

    system_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Системное название статуса (латиница)",
    )
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Отображаемое название статуса",
    )
    color: str = Field(..., max_length=7, description="Цвет в формате #RRGGBB")
    analytic_category: AnalyticCategoryEnum = Field(
        default=AnalyticCategoryEnum.productive,
        description="Аналитическая категория",
    )
    organization_category_id: int | None = Field(
        None,
        description="ID организационной категории",
    )


class StatusCreate(BaseModel):
    """Схема создания статуса."""

    display_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Отображаемое название статуса",
    )
    system_name: str | None = Field(None, description="Системное название статуса (опционально)")
    color: str = Field(..., max_length=7, description="Цвет в формате #RRGGBB")
    analytic_category: AnalyticCategoryEnum = Field(
        default=AnalyticCategoryEnum.productive,
        description="Аналитическая категория",
    )
    organization_category_id: int | None = Field(
        None,
        description="ID организационной категории",
    )
    system_status: bool = Field(
        default=False,
        description="Системный статус (не использует транслитерацию)",
    )
    is_work_status: bool = Field(
        default=False,
        description="Признак рабочего статуса для расчета длительности работы",
    )

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        """Валидируем display_name и проверяем, что оно не пустое."""
        if not v or not v.strip():
            raise ValueError("Отображаемое название статуса не может быть пустым")
        return v.strip()


class StatusUpdate(BaseModel):
    """Схема обновления статуса."""

    system_name: str | None = Field(
        None,
        description="Системное название статуса (может быть null)",
    )
    display_name: str | None = Field(None, min_length=1, max_length=100)
    color: str | None = Field(None, max_length=7)
    analytic_category: AnalyticCategoryEnum | None = None
    organization_category_id: int | None = None
    system_status: bool | None = None
    is_work_status: bool | None = Field(
        None,
        description="Признак рабочего статуса для расчета длительности работы",
    )


class OrganizationCategoryShort(BaseModel):
    """Краткая информация об организационной категории."""

    id: int
    name: str

    class Config:
        """Конфигурация Pydantic модели."""

        from_attributes = True


class StatusResponse(BaseModel):
    """Ответ статуса."""

    id: int = Field(..., description="ID статуса")
    system_name: str = Field(..., description="Системное название статуса (латиница)")
    display_name: str = Field(..., description="Отображаемое название статуса")
    color: str = Field(..., description="Цвет в формате #RRGGBB")
    analytic_category: AnalyticCategoryEnum = Field(..., description="Аналитическая категория")
    analytic_category_display_name: str = Field(
        ...,
        description="Аналитическая категория (отображение)",
    )
    organization_category_id: int | None = Field(
        None,
        description="ID организационной категории",
    )
    organization_category_name: str | None = Field(
        None,
        description="Название организационной категории",
    )
    system_status: bool = Field(..., description="Системный статус")
    is_work_status: bool = Field(
        ...,
        description="Признак рабочего статуса для расчета длительности работы",
    )
    created_at: datetime = Field(..., description="Время создания")
    updated_at: datetime = Field(..., description="Время обновления")

    class Config:
        """Конфигурация Pydantic модели."""

        from_attributes = True

    @classmethod
    def from_orm_with_display(cls, status: Any) -> "StatusResponse":
        """Создать response с отображаемым названием категории."""
        return cls(
            id=status.id,
            system_name=status.system_name,
            display_name=status.display_name,
            color=status.color,
            analytic_category=status.analytic_category,
            analytic_category_display_name=AnalyticCategoryEnum.get_display_name(
                status.analytic_category,
            ),
            organization_category_id=status.organization_category_id,
            organization_category_name=(
                status.organization_category_rel.name if status.organization_category_rel else None
            ),
            system_status=status.system_status,
            is_work_status=status.is_work_status,
            created_at=status.created_at,
            updated_at=status.updated_at,
        )


class StatusListResponse(PaginationBase[StatusResponse]):
    """Ответ списка статусов с пагинацией."""

    pass
