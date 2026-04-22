"""Схема ошибки API (code, detail, entity_id)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class APIError(BaseModel):
    """Тело ответа при ошибке API."""

    code: str
    detail: str
    entity_id: int | UUID | None = None

    model_config = ConfigDict(alias_generator=to_camel)
