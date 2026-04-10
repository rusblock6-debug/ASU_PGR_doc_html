# ruff: noqa: D100, D101

from msgspec import Struct


class EkiperEvent(Struct):
    __tablename__ = "ekiper_events"

    status: str
    value: float
    vehicle_id: str
    sensor_type: str
    timestamp: int
