"""Base factory pattern for service-specific factories."""

from collections.abc import Callable
from typing import Annotated

import asyncpg
from fast_depends import Depends

from src.core.registry import ServiceRegistry
from src.app.postgres_applier import PostgresApplier


def get_applier(
    table: str,
    id_field: str = "id",
) -> Callable[[asyncpg.Pool], PostgresApplier]:
    """
    Создает провайдер для applier'а.

    Example:
        applier: Annotated[
            PostgresApplier,
            Depends(factory.get_applier("users"))
        ]
    """

    def provider(
        pool: Annotated[asyncpg.Pool, Depends(ServiceFactory.get_pool)],
    ) -> PostgresApplier:
        return PostgresApplier(pool=pool, table=table, id_fields=id_field)

    return provider


class ServiceFactory:
    """
    Factory для создания appliers для конкретного service.

    Каждый instance привязан к конкретному ServiceRegistry.
    """

    def __init__(self, service: ServiceRegistry):
        """
        Args:
            service: ServiceRegistry для этого factory
        """
        self._service = service
        self._applier_cache: dict[str, PostgresApplier] = {}

    @property
    def service(self) -> ServiceRegistry:
        """Get associated service."""
        return self._service

    @property
    def pool(self) -> asyncpg.Pool:
        """Get database pool."""
        return self._service.pool

    def get_pool(self) -> asyncpg.Pool:
        """Provider function for DI."""
        return self.pool

    def get_or_create_applier(
        self,
        table: str,
        id_fields: list[str] | str = "id",
    ) -> PostgresApplier:
        """Получить applier для таблицы (с кешированием)."""
        if isinstance(id_fields, str):
            key_fields = [id_fields]
        else:
            key_fields = id_fields

        cache_key = f"{table}:{','.join(key_fields)}"

        if cache_key not in self._applier_cache:
            self._applier_cache[cache_key] = PostgresApplier(
                pool=self.pool,
                table=table,
                id_fields=id_fields,
            )

        return self._applier_cache[cache_key]
