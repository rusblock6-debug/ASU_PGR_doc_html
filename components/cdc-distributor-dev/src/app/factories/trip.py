"""Фабрика для trip service fan-out."""

from src.app.factories.service_factory import ServiceFactory
from src.app.factories.table_config import TRIP_DB_CONFIG
from src.app.multi_table_aggregator import MultiTableAggregator


class TripFactory(ServiceFactory):
    """Factory для trip service — наследует per-bort fan-out от ServiceFactory."""

    @staticmethod
    def get_multi_table_aggregator() -> MultiTableAggregator:
        """Создает multi-table aggregator с конфигом ключей trip-service."""
        return MultiTableAggregator(
            table_configs=TRIP_DB_CONFIG,
            deleted_field="__deleted",
        )
