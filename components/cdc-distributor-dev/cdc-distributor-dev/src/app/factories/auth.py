"""Фабрика для auth service fan-out."""

from src.app.factories.service_factory import ServiceFactory
from src.app.factories.table_config import AUTH_DB_CONFIG
from src.app.multi_table_aggregator import MultiTableAggregator


class AuthFactory(ServiceFactory):
    """Factory для auth service — наследует per-bort fan-out от ServiceFactory."""

    @staticmethod
    def get_multi_table_aggregator() -> MultiTableAggregator:
        """Создает multi-table aggregator с конфигом ключей auth-service."""
        return MultiTableAggregator(
            table_configs=AUTH_DB_CONFIG,
            deleted_field="__deleted",
        )
