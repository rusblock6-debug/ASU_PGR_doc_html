"""Фабрика для graph service fan-out."""

from src.app.factories.service_factory import ServiceFactory
from src.app.factories.table_config import GRAPH_DB_CONFIG
from src.app.multi_table_aggregator import MultiTableAggregator


class GraphFactory(ServiceFactory):
    """Factory для graph service — наследует per-bort fan-out от ServiceFactory."""

    @staticmethod
    def get_multi_table_aggregator() -> MultiTableAggregator:
        """Создает multi-table aggregator с конфигом ключей graph-service."""
        return MultiTableAggregator(
            table_configs=GRAPH_DB_CONFIG,
            deleted_field="__deleted",
        )
