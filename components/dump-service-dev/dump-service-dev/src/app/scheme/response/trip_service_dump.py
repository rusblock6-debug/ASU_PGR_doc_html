# ruff: noqa: D100, D101
from pydantic import BaseModel, ConfigDict

from src.app.scheme.response import File


class TripServiceDump(BaseModel):
    id: int
    trip_id: str
    files: list[File]
    model_config = ConfigDict(from_attributes=True)
