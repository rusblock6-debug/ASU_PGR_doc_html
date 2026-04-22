"""Преобразование типов Debezium в Python типы для PostgreSQL."""

from datetime import datetime, timedelta
from typing import Any
import re


class TypeConverter:
    """
    Конвертер типов Debezium в Python типы для PostgreSQL.

    Debezium использует специальные типы для temporal данных:
    - io.debezium.time.MicroTimestamp -> datetime (микросекунды)
    - io.debezium.time.Timestamp -> datetime (миллисекунды)
    - io.debezium.time.Date -> date (дни с эпохи)
    """

    @staticmethod
    def convert_value(
        value: Any,
        field_type: str,
        field_name: str | None = None,
    ) -> Any:
        """
        Преобразует значение на основе типа поля Debezium.

        Args:
            value: значение для преобразования
            field_type: тип поля из Debezium (field.name)
            field_name: имя поля (опционально, для дополнительного контекста)

        Returns:
            Преобразованное значение
        """
        if value is None:
            return None

        # MicroTimestamp - микросекунды с Unix эпохи
        if field_type == "io.debezium.time.MicroTimestamp":
            return TypeConverter._micros_to_datetime(value)

        # Timestamp - миллисекунды с Unix эпохи
        if field_type == "io.debezium.time.Timestamp":
            return TypeConverter._millis_to_datetime(value)

        # Date - дни с Unix эпохи
        if field_type == "io.debezium.time.Date":
            return TypeConverter._days_to_date(value)

        # PostGIS Geometry - dict с wkb (Well-Known Binary в hex)
        if field_type == "io.debezium.data.geometry.Geometry":
            return TypeConverter._geometry_to_wkb(value)

        # Если это строка с ISO datetime (2025-11-29T00:00:00.000000Z)
        # Парсим её в datetime object для PostgreSQL
        if isinstance(value, str) and TypeConverter._is_iso_datetime(value):
            return TypeConverter._parse_iso_datetime(value)

        # Остальные типы возвращаем как есть
        return value

    @staticmethod
    def _micros_to_datetime(micros: int) -> datetime:
        """Преобразует микросекунды в naive datetime (UTC)."""
        # Используем arithmetic с эпохой для naive datetime
        epoch = datetime(1970, 1, 1)
        return epoch + timedelta(microseconds=micros)

    @staticmethod
    def _millis_to_datetime(millis: int) -> datetime:
        """Преобразует миллисекунды в naive datetime (UTC)."""
        # Используем arithmetic с эпохой для naive datetime
        epoch = datetime(1970, 1, 1)
        return epoch + timedelta(milliseconds=millis)

    @staticmethod
    def _days_to_date(days: int) -> datetime:
        """Преобразует дни с эпохи в naive datetime."""
        from datetime import date, timedelta

        epoch = date(1970, 1, 1)
        result_date = epoch + timedelta(days=days)
        # Преобразуем date в naive datetime (без timezone)
        return datetime.combine(result_date, datetime.min.time())

    @staticmethod
    def _geometry_to_wkb(value: Any) -> str | None:
        """
        Преобразует Debezium geometry в hex-encoded WKB для PostGIS.

        Debezium отправляет geometry как dict: {"wkb": "base64_string", "srid": 4326}
        PostgreSQL/PostGIS ожидает hex-encoded WKB строку.

        Args:
            value: dict с ключом 'wkb' (base64) или строка

        Returns:
            Hex-encoded WKB строку или None
        """
        import base64

        if value is None:
            return None

        # Если это dict - извлечь wkb и конвертировать из base64 в hex
        if isinstance(value, dict):
            wkb_base64 = value.get("wkb")
            if wkb_base64:
                # Декодируем base64 → binary
                wkb_binary = base64.b64decode(wkb_base64)
                # Конвертируем binary → hex (uppercase для PostGIS)
                return wkb_binary.hex().upper()
            return None

        # Если это строка - попробуем декодировать как base64
        if isinstance(value, str):
            try:
                wkb_binary = base64.b64decode(value)
                return wkb_binary.hex().upper()
            except Exception:
                # Если не base64, вернуть как есть (возможно уже hex)
                return value

        # Неизвестный формат - вернуть как есть
        return value

    @staticmethod
    def _is_iso_datetime(value: str) -> bool:
        """
        Проверяет, является ли строка ISO datetime форматом.

        Примеры:
        - 2025-11-29T00:00:00.000000Z
        - 2025-11-29T12:34:56Z
        - 2025-11-29T12:34:56.123Z
        """
        # Простая проверка на паттерн ISO datetime
        iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        return bool(re.match(iso_pattern, value))

    @staticmethod
    def _parse_iso_datetime(value: str) -> datetime:
        """
        Парсит ISO datetime строку в naive datetime для PostgreSQL.

        Args:
            value: ISO datetime строка (e.g., "2025-11-29T00:00:00.000000Z")

        Returns:
            Naive datetime object (без timezone info)
        """
        # Убираем 'Z' в конце если есть
        value = value.rstrip("Z")

        # Парсим ISO формат
        try:
            # Попробуем с микросекундами
            dt = datetime.fromisoformat(value)
        except ValueError:
            # Если не получилось, пробуем без микросекунд
            try:
                dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                # Последняя попытка - с миллисекундами
                dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")

        # Убираем timezone info, PostgreSQL ожидает naive datetime
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)

        return dt
