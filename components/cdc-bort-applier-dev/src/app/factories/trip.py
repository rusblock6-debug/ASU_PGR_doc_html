"""Фабрика для создания trip applier'ов с DI."""

from src.app.factories.service_factory import ServiceFactory
from src.app.factories.table_config import TRIP_DB_CONFIG
from src.app.postgres_applier import PostgresApplier
from src.core.registry import ServiceRegistry


class TripFactory(ServiceFactory):
    """Factory для trip service."""

    def __init__(self, service: ServiceRegistry):
        super().__init__(service)

    def get_or_create_applier(
        self,
        table: str,
        id_fields: list[str] | str | None = None,
    ) -> PostgresApplier:
        if id_fields is None:
            id_fields = TRIP_DB_CONFIG.get_primary_keys(table)
        return super().get_or_create_applier(table, id_fields)
