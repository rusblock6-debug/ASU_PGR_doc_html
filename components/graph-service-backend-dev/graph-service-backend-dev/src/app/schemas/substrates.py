"""Pydantic модели для подложек (substrates)"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import PaginationBase, TimestampBase


class Center(BaseModel):
    """Модель центра подложки"""

    x: float = Field(0.0, description="Координата X центра")
    y: float = Field(0.0, description="Координата Y центра")


class SubstrateCreate(BaseModel):
    """Модель для создания подложки"""

    file_content: bytes = Field(..., description="Содержимое DXF файла в байтах")
    filename: str = Field(..., description="Имя файла")
    horizon_id: int | None = Field(None, description="ID горизонта")
    opacity: int = Field(100, ge=0, le=100, description="Прозрачность от 0 до 100")
    center: Center = Field(
        default_factory=lambda: Center(x=0.0, y=0.0),
        description="Центр подложки",
    )


class SubstrateUpdate(BaseModel):
    """Модель для обновления подложки (частичное обновление)."""

    horizon_id: int | None = Field(None, description="ID горизонта; null — без горизонта")
    opacity: int | None = Field(None, ge=0, le=100, description="Прозрачность от 0 до 100")
    center: Center | None = Field(None, description="Центр подложки")


class SubstrateResponse(TimestampBase):
    """Модель ответа для подложки"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID подложки")
    horizon_id: int | None = Field(None, description="ID горизонта")
    original_filename: str = Field(..., description="Оригинальное имя файла")
    path_s3: str = Field(..., description="Путь к файлу в S3")
    opacity: int = Field(..., description="Прозрачность от 0 до 100")
    center: Center = Field(..., description="Центр подложки")

    @field_validator("center", mode="before")
    @classmethod
    def validate_center(cls, v: Any) -> Center:
        """Конвертирует словарь в модель Center"""
        if isinstance(v, dict):
            return Center(**v)
        if isinstance(v, Center):
            return v
        raise ValueError(f"Некорректный тип для center: {type(v)}")


class SubstrateListResponse(PaginationBase[SubstrateResponse]):
    """Пагинированный список подложек."""

    pass


class SubstrateWithSvgResponse(SubstrateResponse):
    """Модель ответа для подложки со ссылкой на SVG в S3."""

    svg_link: str = Field(..., description="Ссылка на SVG файл в S3 (временная или публичная)")
