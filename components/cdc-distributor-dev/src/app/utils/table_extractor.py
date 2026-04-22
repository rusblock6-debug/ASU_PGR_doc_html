"""Извлечение имени таблицы из schema.name."""


def extract_table_name(schema_name: str) -> str:
    """Извлекает имя таблицы из Debezium schema.name.

    Args:
        schema_name: полное имя вида "appdb.public.users.Value"

    Returns:
        Имя таблицы, например "users"

    Examples:
        >>> extract_table_name("appdb.public.users.Value")
        "users"
        >>> extract_table_name("mydb.schema.orders.Value")
        "orders"
        >>> extract_table_name("users")
        "users"
    """
    if not schema_name:
        raise ValueError("schema_name cannot be empty")

    # Debezium format: "{connector}.{schema}.{table}.Value"
    # Берём предпоследний элемент
    parts = schema_name.split(".")

    if len(parts) >= 2:
        # "appdb.public.users.Value" → "users"
        return parts[-2]

    # Fallback для простых имен
    return parts[0] if parts else schema_name
