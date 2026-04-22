"""Базовая фабрика для работы с БД через DI."""

from collections.abc import Callable
from typing import Annotated

import asyncpg
from fast_depends import Depends

from src.core.registry import ServiceRegistry
from src.app.postgres_applier import PostgresApplier


class BaseFactory:
    """
    Базовая фабрика для создания applier'ов.

    Используется как базовый класс для специализированных фабрик (GraphFactory и т.д.).
    """

    def __init__(
        self,
        service: ServiceRegistry | None = None,
        get_pool: Callable[[], asyncpg.Pool] | None = None,
    ) -> None:
        """
        Args:
            service: ServiceRegistry for this factory (new pattern)
            get_pool: Pool provider function (backward compatible)
        """
        self._service: ServiceRegistry | None
        self._get_pool: Callable[[], asyncpg.Pool]

        if service is not None:
            self._service = service
            self._get_pool = lambda: service.pool
        elif get_pool is not None:
            self._service = None
            self._get_pool = get_pool
        else:
            raise ValueError("Either service or get_pool must be provided")

        self._applier_cache: dict[str, PostgresApplier] = {}

    @property
    def service(self) -> ServiceRegistry | None:
        """Get associated service (if using new pattern)."""
        return self._service

    def get_applier(
        self,
        table: str,
        id_field: str = "id",
    ) -> Callable[[asyncpg.Pool], PostgresApplier]:
        """
        Создаёт провайдер для applier'а.

        Args:
            table: имя таблицы
            id_field: имя поля ID

        Returns:
            Функция-провайдер для DI

        Example:
            applier: Annotated[
                PostgresApplier,
                Depends(factory.get_applier("users"))
            ]
        """

        def provider(
            pool: Annotated[asyncpg.Pool, Depends(self._get_pool)],
        ) -> PostgresApplier:
            return PostgresApplier(pool=pool, table=table, id_fields=id_field)

        return provider

    def get_or_create_applier(
        self,
        table: str,
        id_fields: list[str] | str = "id",
    ) -> PostgresApplier:
        """
        Получить applier для таблицы (с кешированием).

        Args:
            table: имя таблицы
            id_fields: имя поля ID или список полей для составного ключа

        Returns:
            PostgresApplier для таблицы

        Примечание:
            Applier'ы кешируются для переиспользования.
        """
        # Нормализуем id_fields для ключа кеша
        if isinstance(id_fields, str):
            key_fields = [id_fields]
        else:
            key_fields = id_fields

        cache_key = f"{table}:{','.join(key_fields)}"

        if cache_key not in self._applier_cache:
            pool = self._get_pool()
            self._applier_cache[cache_key] = PostgresApplier(
                pool=pool,
                table=table,
                id_fields=id_fields,
            )

        return self._applier_cache[cache_key]
