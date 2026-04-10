"""Pydantic схемы для сущности Ladder."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationBase, TimestampBase


class LadderBase(BaseModel):
    """Базовые поля лестницы."""

    from_horizon_id: int = Field(..., description="ID горизонта начала лестницы")
    to_horizon_id: int = Field(..., description="ID горизонта конца лестницы")
    is_active: bool = Field(False, description="Активна ли лестница")
    is_completed: bool = Field(False, description="Завершено ли строительство")


class LadderCreate(LadderBase):
    """Схема создания лестницы."""

    id: int | None = Field(
        None,
        description="ID лестницы (опционально, для синхронизации с сервером)",
    )


class LadderUpdate(BaseModel):
    """Схема частичного обновления лестницы."""

    from_horizon_id: int | None = Field(
        None,
        description="ID горизонта начала лестницы",
    )
    to_horizon_id: int | None = Field(None, description="ID горизонта конца лестницы")
    is_active: bool | None = Field(None, description="Активна ли лестница")
    is_completed: bool | None = Field(None, description="Завершено ли строительство")


class LadderResponse(TimestampBase, LadderBase):
    """Полная схема ответа по лестнице."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID лестницы")


class LadderListResponse(PaginationBase[LadderResponse]):
    """Список лестниц с пагинацией."""


class LadderConnect(BaseModel):
    """Схема создания лестницы между двумя узлами."""

    from_node_id: int = Field(..., description="ID начального узла")
    to_node_id: int = Field(..., description="ID конечного узла")
