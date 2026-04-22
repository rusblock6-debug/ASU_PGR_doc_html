"""Базовые Pydantic schemas для API."""

from pydantic import BaseModel as PydanticModel
from pydantic import ConfigDict


class APIBaseModel(PydanticModel):
    """Базовая модель API с общей конфигурацией."""

    model_config = ConfigDict(
        from_attributes=True,
    )
