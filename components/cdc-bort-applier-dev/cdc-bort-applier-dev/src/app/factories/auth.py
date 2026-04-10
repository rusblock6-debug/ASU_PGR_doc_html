"""Фабрика для создания auth applier'ов с DI."""

from src.app.factories.service_factory import ServiceFactory
from src.core.registry import ServiceRegistry
from src.app.postgres_applier import PostgresApplier
from src.app.factories.table_config import AUTH_DB_CONFIG


class AuthFactory(ServiceFactory):
    """
    Factory для auth service.
    """

    def __init__(self, service: ServiceRegistry):
        super().__init__(service)

    def get_or_create_applier(
        self,
        table: str,
        id_fields: list[str] | str | None = None,
    ) -> PostgresApplier:
        """
        Создаёт applier с учётом primary keys из конфигурации.

        Args:
            table: имя таблицы
            id_fields: явно указанные поля ключа (если None - берутся из AUTH_DB_CONFIG)

        Returns:
            PostgresApplier для таблицы
        """
        # Если id_fields не указан - берём из конфига
        if id_fields is None:
            id_fields = AUTH_DB_CONFIG.get_primary_keys(table)

        return super().get_or_create_applier(table, id_fields)
