# ruff: noqa: D100, D101

from datetime import datetime

from msgspec import Struct


class CycleTagHistory(Struct):
    __tablename__ = "cycle_tag_history"

    id: str
    timestamp: datetime
    vehicle_id: int
    cycle_id: str | None
    place_id: int
    place_name: str
    place_type: str
    tag_id: int
    tag_name: str
    tag_event: str
