"""Фабрика для enterprise service fan-out."""

from src.app.factories.service_factory import ServiceFactory
from src.app.factories.table_config import ENTERPRISE_DB_CONFIG
from src.app.multi_table_aggregator import MultiTableAggregator


class EnterpriseFactory(ServiceFactory):
    """Factory для enterprise service — наследует per-bort fan-out от ServiceFactory."""

    @staticmethod
    def get_multi_table_aggregator() -> MultiTableAggregator:
        """Создает multi-table aggregator с конфигом ключей enterprise-service."""
        return MultiTableAggregator(
            table_configs=ENTERPRISE_DB_CONFIG,
            deleted_field="__deleted",
        )
