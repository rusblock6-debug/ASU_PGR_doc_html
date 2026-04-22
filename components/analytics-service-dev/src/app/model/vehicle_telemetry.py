# ruff: noqa: D100, D101

from msgspec import Struct


class VehicleTelemetry(Struct):
    __tablename__ = "vehicle_telemetry"

    bort: int
    timestamp: int
    lat: float
    lon: float
    height: float | None
    speed: float | None
    fuel: float | None
