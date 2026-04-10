"""Агрегатор для CDC событий из нескольких таблиц."""

from collections import defaultdict
from typing import Any

from src.app.factories.table_config import DatabaseConfig
from src.app.model import Envelope, Schema
from src.app.utils.table_extractor import extract_table_name
from src.app.utils.type_converter import TypeConverter
from src.core.aggregator import AggregatedBatch


class MultiTableAggregator:
    """Группирует CDC события по таблицам, затем по ID.

    Для каждой таблицы применяет логику:
    - delete побеждает всё
    - иначе last wins (последний upsert)
    """

    def __init__(
        self,
        table_configs: DatabaseConfig,
        deleted_field: str = "__deleted",
    ) -> None:
        """Инициализация MultiTableAggregator.

        Args:
            table_configs: маппинг {table_name: [key_fields]}.
                Если None - используется ["id"] для всех таблиц.
            deleted_field: поле для метки удаления.
        """
        self._table_configs = table_configs
        self._deleted_field = deleted_field

    def aggregate(
        self,
        events: list[Envelope],
    ) -> dict[str, AggregatedBatch[dict[str, Any]]]:
        """Агрегирует события по таблицам.

        Args:
            events: список CDC событий (Envelope)

        Returns:
            dict[table_name, AggregatedBatch]
            где каждый AggregatedBatch содержит upserts и deletes для таблицы

        Example:
            {
                "users": AggregatedBatch(upserts=[...], deletes=[1, 2]),
                "orders": AggregatedBatch(upserts=[...], deletes=[]),
            }
        """
        # Группировка по таблицам (с преобразованием типов)
        tables: dict[str, list[dict[str, Any]]] = defaultdict(list)
        table_schemas: dict[str, Schema] = {}

        for event in events:
            table_name = extract_table_name(event.schema.name)

            # Сохраняем schema для таблицы (для преобразования типов)
            if table_name not in table_schemas:
                table_schemas[table_name] = event.schema

            # Преобразуем типы в payload
            converted_payload = self._convert_payload_types(event.payload, event.schema)
            tables[table_name].append(converted_payload)

        # Агрегация внутри каждой таблицы
        result: dict[str, AggregatedBatch[dict[str, Any]]] = {}

        for table_name, payloads in tables.items():
            result[table_name] = self._aggregate_table(table_name, payloads)

        return result

    @staticmethod
    def _convert_payload_types(
        payload: dict[str, Any],
        schema: Schema,
    ) -> dict[str, Any]:
        """Преобразует типы в payload на основе schema.

        Args:
            payload: данные события
            schema: схема Debezium с описанием типов

        Returns:
            Payload с преобразованными типами
        """
        # Создаём маппинг field_name -> field_type_name
        field_types: dict[str, str] = {}
        for field in schema.fields:
            # Используем semantic type (name) если есть, иначе базовый type
            field_types[field.field] = field.name if field.name else field.type

        # Преобразуем значения
        converted = {}
        for key, value in payload.items():
            field_type = field_types.get(key, "")
            converted[key] = TypeConverter.convert_value(value, field_type, key)

        return converted

    def _aggregate_table(
        self,
        table_name: str,
        payloads: list[dict[str, Any]],
    ) -> AggregatedBatch[dict[str, Any]]:
        """Агрегирует события для одной таблицы."""
        # Получаем ключевые поля для таблицы
        key_fields = self._table_configs.get_primary_keys(table_name)

        grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
        deleted_ids: set[tuple[Any, ...]] = set()

        for payload in payloads:
            # Создаём composite key как tuple
            record_key = tuple(payload.get(field) for field in key_fields)

            # Пропускаем если какое-то поле ключа None
            if None in record_key:
                continue

            is_deleted = payload.get(self._deleted_field) == "true"

            if is_deleted:
                deleted_ids.add(record_key)
                grouped.pop(record_key, None)
            else:
                # INSERT/UPDATE после DELETE — INSERT побеждает
                deleted_ids.discard(record_key)
                grouped[record_key] = payload

        # Преобразуем deleted_ids обратно в формат для applier
        if len(key_fields) == 1:
            # Для одного ключа возвращаем скаляры
            deletes = [key[0] for key in deleted_ids]
        else:
            # Для составных ключей возвращаем dict
            deletes = [{field: key[i] for i, field in enumerate(key_fields)} for key in deleted_ids]

        return AggregatedBatch(
            upserts=list(grouped.values()),
            deletes=deletes,
        )
