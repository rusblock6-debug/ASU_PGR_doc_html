# ruff: noqa: D100, D101
from src.app.model import EkiperEvent
from src.core.repository import ClickHouseRepository


class EkiperEventsRepository(ClickHouseRepository[EkiperEvent]):
    pass
