# ruff: noqa: D100, D101

from msgspec import Struct


class GpsData(Struct):
    __tablename__ = "gps_data"

    bort: str
    timestamp: int
    height: float | None
    lat: float
    lon: float
