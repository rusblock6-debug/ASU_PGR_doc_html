"""Утилиты валидации для graph-service"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def validate_coordinates(
    lat: float | None,
    lon: float | None,
    height: float | None = None,
) -> tuple[bool, dict[str, Any]]:
    """Валидация GPS координат

    Args:
        lat: Широта
        lon: Долгота
        height: Высота (опционально)

    Returns:
        Кортеж (is_valid, errors_dict)
    """
    errors = {}

    # Проверка широты
    if lat is None:
        errors["lat"] = "Широта не может быть пустой"
    elif not isinstance(lat, (int, float)):
        errors["lat"] = "Широта должна быть числом"
    elif not -90 <= lat <= 90:
        errors["lat"] = "Широта должна быть в диапазоне от -90 до 90 градусов"

    # Проверка долготы
    if lon is None:
        errors["lon"] = "Долгота не может быть пустой"
    elif not isinstance(lon, (int, float)):
        errors["lon"] = "Долгота должна быть числом"
    elif not -180 <= lon <= 180:
        errors["lon"] = "Долгота должна быть в диапазоне от -180 до 180 градусов"

    # Проверка высоты
    if height is not None:
        if not isinstance(height, (int, float)):
            errors["height"] = "Высота должна быть числом"
        elif not -1000 <= height <= 1000:  # Разумные пределы для шахты
            errors["height"] = "Высота должна быть в диапазоне от -1000 до 1000 метров"

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_tag_data(data: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Валидация данных метки

    Args:
        data: Словарь с данными метки

    Returns:
        Кортеж (is_valid, errors_dict)
    """
    errors = {}

    # Проверка обязательных полей (только для создания, не для обновления)
    required_fields = ["name", "point_type", "point_id"]
    for field in required_fields:
        if field in data and not data[field]:
            errors[field] = f"Поле {field} не может быть пустым"

    # ✅ НЕ валидируем координаты - это Canvas координаты, не GPS!
    # Canvas координаты могут быть любыми числами (x, y, z)
    # Валидация координат как GPS lat/lon НЕ применима к Canvas

    # Валидация радиуса
    radius = data.get("radius")
    if radius is not None:
        if not isinstance(radius, (int, float)):
            errors["radius"] = "Радиус должен быть числом"
        elif radius <= 0:
            errors["radius"] = "Радиус должен быть положительным числом"
        elif radius > 1000:  # Разумный предел
            errors["radius"] = "Радиус не должен превышать 1000 метров"

    # Валидация типа точки с нормализацией
    valid_point_types = ["loading", "unloading", "transfer", "transit", "transport"]
    point_type = data.get("point_type")
    if point_type:
        # Нормализуем тип перед проверкой
        normalized_type = normalize_point_type(point_type)
        if normalized_type not in valid_point_types:
            errors["point_type"] = f"Тип точки должен быть одним из: {', '.join(valid_point_types)}"
        else:
            # Обновляем point_type в данных на нормализованное значение
            data["point_type"] = normalized_type

    # Валидация MAC адреса (если указан)
    beacon_mac = data.get("beacon_mac")
    if beacon_mac:
        # Поддерживаем форматы: XX:XX:XX:XX:XX:XX или XX-XX-XX-XX-XX-XX или XXXXXXXXXXXX
        mac_pattern = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^[0-9A-Fa-f]{12}$")
        if not mac_pattern.match(beacon_mac):
            errors["beacon_mac"] = (
                "MAC адрес должен быть в формате XX:XX:XX:XX:XX:XX или XX-XX-XX-XX-XX-XX"
            )

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_level_data(data: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Валидация данных уровня

    Args:
        data: Словарь с данными уровня

    Returns:
        Кортеж (is_valid, errors_dict)
    """
    errors = {}

    # Проверка названия
    name = data.get("name")
    if not name or not isinstance(name, str) or len(name.strip()) == 0:
        errors["name"] = "Название уровня обязательно и должно быть непустой строкой"
    elif len(name) > 100:
        errors["name"] = "Название уровня не должно превышать 100 символов"

    # Проверка высоты
    height = data.get("height")
    if height is None:
        errors["height"] = "Высота уровня обязательна"
    elif not isinstance(height, (int, float)):
        errors["height"] = "Высота должна быть числом"
    elif not -1000 <= height <= 0:  # Уровни шахты обычно отрицательные
        errors["height"] = "Высота уровня должна быть в диапазоне от -1000 до 0 метров"

    # Проверка описания
    description = data.get("description")
    if description is not None:
        if not isinstance(description, str):
            errors["description"] = "Описание должно быть строкой"
        elif len(description) > 500:
            errors["description"] = "Описание не должно превышать 500 символов"

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_node_data(data: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Валидация данных узла графа

    Args:
        data: Словарь с данными узла

    Returns:
        Кортеж (is_valid, errors_dict)
    """
    errors = {}

    # ✅ НЕ валидируем координаты - это Canvas координаты, не GPS!
    # Canvas координаты могут быть любыми числами (x, y, z)
    # Валидация координат как GPS lat/lon НЕ применима к Canvas

    # Валидация типа узла
    valid_node_types = ["road", "junction", "station", "entrance", "ladder"]
    node_type = data.get("node_type", "road")
    if node_type and node_type not in valid_node_types:
        errors["node_type"] = f"Тип узла должен быть одним из: {', '.join(valid_node_types)}"
    if node_type == "ladder" and data.get("ladder_id") is None:
        errors["ladder_id"] = "Для node_type='ladder' поле ladder_id обязательно"

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_edge_data(data: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Валидация данных ребра графа

    Args:
        data: Словарь с данными ребра

    Returns:
        Кортеж (is_valid, errors_dict)
    """
    errors = {}

    # Проверка ID узлов
    from_node_id = data.get("from_node_id")
    to_node_id = data.get("to_node_id")

    if from_node_id is None:
        errors["from_node_id"] = "ID начального узла обязателен"
    elif not isinstance(from_node_id, int) or from_node_id <= 0:
        errors["from_node_id"] = "ID начального узла должен быть положительным целым числом"

    if to_node_id is None:
        errors["to_node_id"] = "ID конечного узла обязателен"
    elif not isinstance(to_node_id, int) or to_node_id <= 0:
        errors["to_node_id"] = "ID конечного узла должен быть положительным целым числом"

    # Проверка что узлы не одинаковы
    if from_node_id == to_node_id:
        errors["nodes"] = "Начальный и конечный узлы не могут быть одинаковыми"

    is_valid = len(errors) == 0
    return is_valid, errors


def handle_validation_errors(errors: dict[str, Any], context: str = "Операция") -> dict[str, Any]:
    """Форматирование ошибок валидации для ответа API

    Args:
        errors: Словарь с ошибками
        context: Контекст операции

    Returns:
        Словарь для ответа API
    """
    logger.warning(f"{context} не удалась. Ошибки валидации: {errors}")

    return {
        "error": "Ошибка валидации данных",
        "details": errors,
        "context": context,
    }


def safe_float_conversion(value: Any, default: float | None = None) -> float | None:
    """Безопасное преобразование в float

    Args:
        value: Значение для преобразования
        default: Значение по умолчанию при ошибке

    Returns:
        float или None
    """
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        logger.warning(f"Не удалось преобразовать {value} в float")
        return default


def safe_int_conversion(value: Any, default: int | None = None) -> int | None:
    """Безопасное преобразование в int

    Args:
        value: Значение для преобразования
        default: Значение по умолчанию при ошибке

    Returns:
        int или None
    """
    try:
        if value is None:
            return default
        return int(value)
    except (ValueError, TypeError):
        logger.warning(f"Не удалось преобразовать {value} в int")
        return default


def normalize_point_type(raw_type: str) -> str:
    """Нормализация типа точки из импортируемых данных в допустимые типы.

    Новые типы меток:
    - loading - Погрузочная
    - unloading - Разгрузочная
    - transfer - Перегрузочная
    - transit - Транзитная
    - transport - Транспортная

    Маппинг старых типов на новые (для обратной совместимости):
    - checkpoint → transit
    - shovel → loading
    - dump_site → transfer
    - unload → unloading
    - fuel_station, idle_area, parking → transport (транспортная)

    Args:
        raw_type: Исходный тип из импортируемых данных

    Returns:
        Нормализованный тип из допустимого списка
    """
    if not raw_type:
        return "transit"  # Тип по умолчанию

    raw_type_lower = raw_type.lower().strip()

    # Маппинг старых типов на новые (для обратной совместимости)
    old_to_new = {
        "checkpoint": "transit",
        "shovel": "loading",
        "dump_site": "transfer",
        "unload": "unloading",
        "fuel_station": "transport",
        "idle_area": "transport",
        "parking": "transport",
    }

    # Если это уже новый тип, возвращаем как есть
    if raw_type_lower in ["loading", "unloading", "transfer", "transit", "transport"]:
        return raw_type_lower

    # Если это старый тип, маппим на новый
    if raw_type_lower in old_to_new:
        return old_to_new[raw_type_lower]

    # Маппинги типов из импорта - проверяем более специфичные типы ПЕРВЫМИ

    # Проверяем loading (погрузочная) - включает shovel, excavator
    loading_aliases = [
        "shovel",
        "excavator",
        "экскаватор",
        "loading",
        "погрузка",
        "погрузки",
        "погрузочная",
    ]
    for alias in loading_aliases:
        if alias in raw_type_lower:
            return "loading"

    # Проверяем unloading (разгрузочная)
    unloading_aliases = ["unload", "unloading", "разгрузка", "разгрузки", "разгрузочная"]
    for alias in unloading_aliases:
        if alias in raw_type_lower:
            return "unloading"

    # Проверяем transfer (перегрузочная)
    transfer_aliases = [
        "dump",
        "dump_site",
        "выгрузка",
        "отвал",
        "transfer",
        "перегрузка",
        "перегрузки",
        "перегрузочная",
    ]
    for alias in transfer_aliases:
        if alias in raw_type_lower:
            return "transfer"

    # Проверяем transport (транспортная) - включает fuel_station, idle_area, parking
    transport_aliases = [
        "fuel_station",
        "топливная",
        "топливо",
        "idle_area",
        "idle",
        "зона_отдыха",
        "отдыха",
        "parking",
        "стоянка",
        "стоянки",
        "transport",
        "транспорт",
        "транспортная",
    ]
    for alias in transport_aliases:
        if alias in raw_type_lower:
            return "transport"

    # Проверяем transit (транзитная)
    transit_aliases = [
        "checkpoint",
        "контрольная",
        "контрольная_точка",
        "transit",
        "транзит",
        "транзитное",
        "транзитная",
    ]
    for alias in transit_aliases:
        if alias in raw_type_lower:
            return "transit"

    # Всё остальное → transit
    logger.debug(f"Неизвестный тип точки '{raw_type}', используется 'transit' по умолчанию")
    return "transit"
