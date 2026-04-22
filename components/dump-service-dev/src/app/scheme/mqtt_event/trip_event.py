# ruff: noqa: D100, D101

from pydantic import BaseModel

from src.app.type import TripStatus


class TripEvent(BaseModel):
    cycle_id: str
    event_type: TripStatus
