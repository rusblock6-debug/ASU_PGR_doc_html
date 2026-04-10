"""Базовая модель pydentic для API роутеров."""

from pydantic import BaseModel, ConfigDict


class APIBaseModel(BaseModel):
    """Базовая модель работы для сериализации SQLAlchemy."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")
