# ruff: noqa: D100, D101
from src.app.model import GpsData
from src.core.repository import ClickHouseRepository


class GpsDataRepository(ClickHouseRepository[GpsData]):
    pass
