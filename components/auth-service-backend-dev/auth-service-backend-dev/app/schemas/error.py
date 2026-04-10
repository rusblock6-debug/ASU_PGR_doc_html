from typing import Any

from pydantic import BaseModel


class APIError(BaseModel):
    code: str
    detail: str
    entity_id: Any | None = None
