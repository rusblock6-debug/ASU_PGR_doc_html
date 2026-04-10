"""Конфигурация таблиц БД с первичными ключами."""

import msgspec


class TableConfig(msgspec.Struct, frozen=True):
    """Конфигурация таблицы с первичными ключами."""

    name: str
    primary_keys: list[str]


class DatabaseConfig(msgspec.Struct, frozen=True):
    """Конфигурация всех таблиц БД."""

    tables: list[TableConfig]

    def get_primary_keys(self, table_name: str) -> list[str]:
        """
        Получить список первичных ключей для таблицы.

        Args:
            table_name: имя таблицы

        Returns:
            Список полей первичного ключа (или ["id"] по умолчанию)
        """
        for table in self.tables:
            if table.name == table_name:
                return table.primary_keys
        return ["id"]

    def to_dict(self) -> dict[str, list[str]]:
        """Преобразовать в dict для обратной совместимости."""
        return {table.name: table.primary_keys for table in self.tables}


# Конфигурация таблиц graph БД
GRAPH_DB_CONFIG = DatabaseConfig(
    tables=[
        # Таблицы с одним ключом
        TableConfig(name="graph_edges", primary_keys=["id"]),
        TableConfig(name="graph_nodes", primary_keys=["id"]),
        TableConfig(name="horizons", primary_keys=["id"]),
        TableConfig(name="place_load", primary_keys=["id"]),
        TableConfig(name="place_reload", primary_keys=["id"]),
        TableConfig(name="place_unload", primary_keys=["id"]),
        TableConfig(name="places", primary_keys=["id"]),
        TableConfig(name="sections", primary_keys=["id"]),
        TableConfig(name="shafts", primary_keys=["id"]),
        TableConfig(name="tags", primary_keys=["id"]),
        TableConfig(name="tags", primary_keys=["id"]),
        # Таблицы связей с составными ключами
        TableConfig(name="section_horizons", primary_keys=["section_id", "horizon_id"]),
        TableConfig(name="shaft_horizons", primary_keys=["shaft_id", "horizon_id"]),
    ],
)


# Конфигурация таблиц enterprise БД
ENTERPRISE_DB_CONFIG = DatabaseConfig(
    tables=[
        # Таблицы с одним ключом
        TableConfig(name="enterprise_settings", primary_keys=["id"]),
        TableConfig(name="load_type_categories", primary_keys=["id"]),
        TableConfig(name="load_types", primary_keys=["id"]),
        TableConfig(name="organization_categories", primary_keys=["id"]),
        TableConfig(name="route_tasks", primary_keys=["id"]),
        TableConfig(name="shift_tasks", primary_keys=["id"]),
        TableConfig(name="statuses", primary_keys=["id"]),
        TableConfig(name="vehicle_models", primary_keys=["id"]),
        TableConfig(name="vehicles", primary_keys=["id"]),
        TableConfig(name="work_regimes", primary_keys=["id"]),
        # Таблицы связей с составными ключами
    ],
)

# Конфигурация таблиц auth БД
AUTH_DB_CONFIG = DatabaseConfig(
    tables=[
        # Таблицы с одним ключом
        TableConfig(name="permissions", primary_keys=["id"]),
        TableConfig(name="roles", primary_keys=["id"]),
        TableConfig(name="staff", primary_keys=["id"]),
        TableConfig(name="users", primary_keys=["id"]),
        # Таблицы связей с составными ключами
        TableConfig(name="role_permissions", primary_keys=["role_id", "permission_id"]),
    ],
)

# Конфигурация таблиц trip_service БД
TRIP_DB_CONFIG = DatabaseConfig(
    tables=[
        # Таблицы с одним ключом
        TableConfig(name="shift_tasks", primary_keys=["id"]),
        TableConfig(name="route_tasks", primary_keys=["id"]),
    ],
)
