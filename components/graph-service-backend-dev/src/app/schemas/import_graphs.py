"""Pydantic схемы для импорта графов из внешних источников"""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ImportNode(BaseModel):
    """Схема узла из внешнего источника"""

    id: Any = Field(..., description="ID узла из внешнего источника")
    x: float = Field(..., description="Координата X")
    y: float = Field(..., description="Координата Y")
    z: float | None = Field(None, description="Координата Z (высота)")
    node_type: str | None = Field("road", description="Тип узла")
    # Дополнительные поля
    properties: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Дополнительные свойства",
    )


class ImportEdge(BaseModel):
    """Схема ребра из внешнего источника"""

    id: Any | None = Field(None, description="ID ребра из внешнего источника")
    from_node: Any = Field(..., description="ID начального узла", alias="from")
    to_node: Any = Field(..., description="ID конечного узла", alias="to")
    edge_type: str | None = Field("horizontal", description="Тип ребра")
    direction: str | None = Field("Двунаправленное", description="Направление дороги")
    weight: float | None = Field(None, description="Вес ребра")
    # Дополнительные поля
    properties: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Дополнительные свойства",
    )

    model_config = ConfigDict(populate_by_name=True)  # Разрешить использование alias


class ImportTag(BaseModel):
    """Схема метки из внешнего источника"""

    id: Any | None = Field(
        None,
        description="ID метки из внешнего источника (автогенерируется если не указан)",
    )
    x: float = Field(..., description="Координата X")
    y: float = Field(..., description="Координата Y")
    z: float | None = Field(None, description="Координата Z")
    radius: float | None = Field(25.0, description="Радиус действия")
    name: str = Field(..., description="Название метки")
    point_type: str | None = Field("transit", description="Тип точки")
    point_id: str | None = Field(None, description="ID точки (обратная совместимость)")
    beacon_id: str | None = Field(None, description="Уникальная ID метки (beacon_id)")
    beacon_mac: str | None = Field(None, description="MAC адрес метки (beacon_mac)")
    beacon_place: str | None = Field(None, description="Место установки (beacon_place)")
    # Дополнительные поля
    properties: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Дополнительные свойства",
    )

    @field_validator("point_id")
    @classmethod
    def validate_point_id_format(cls, v: str | None) -> str | None:
        """Валидация формата point_id"""
        if v is None:
            return v
        if not v.strip():
            raise ValueError("point_id не может быть пустым")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("point_id может содержать только буквы, цифры, дефис и подчеркивание")
        return v.strip()

    @field_validator("beacon_mac")
    @classmethod
    def validate_beacon_mac_format(cls, v: str | None) -> str | None:
        """Валидация формата MAC адреса"""
        if not v:
            return None
        v = v.strip()
        if not v:
            return None
        # Поддерживаем форматы: XX:XX:XX:XX:XX:XX или XX-XX-XX-XX-XX-XX или XXXXXXXXXXXX
        mac_pattern = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^[0-9A-Fa-f]{12}$")
        if not mac_pattern.match(v):
            raise ValueError(
                "MAC адрес должен быть в формате XX:XX:XX:XX:XX:XX или XX-XX-XX-XX-XX-XX",
            )
        # Нормализуем к формату с двоеточиями
        v_clean = v.replace("-", "").replace(":", "").upper()
        return ":".join([v_clean[i : i + 2] for i in range(0, 12, 2)])


class ImportHorizon(BaseModel):
    """Схема уровня из внешнего источника"""

    id: Any | None = Field(None, description="ID уровня из внешнего источника")
    name: str = Field(..., description="Название уровня")
    height: float = Field(..., description="Высота уровня")
    description: str | None = Field(None, description="Описание")
    nodes: list[ImportNode] = Field(default_factory=list, description="Узлы на уровне")
    edges: list[ImportEdge] = Field(default_factory=list, description="Рёбра на уровне")
    tags: list[ImportTag] = Field(default_factory=list, description="Метки на уровне")


class ImportGraphRequest(BaseModel):
    """Запрос на импорт графа"""

    source_url: str | None = Field(None, description="URL внешнего API для загрузки графа")
    source_data: dict[str, Any] | None = Field(
        None,
        description="Данные графа напрямую (если не используется URL)",
    )
    overwrite_existing: bool = Field(False, description="Перезаписать существующие горизонты")
    horizon_id: int | None = Field(
        None,
        description="ID целевого горизонта (если импортируем в существующий)",
    )
    create_nodes_with_tags: bool = Field(True, description="Создавать метки для каждого узла")
    tag_radius: float = Field(10.0, description="Радиус меток (в метрах)")


class ImportGraphData(BaseModel):
    """Структура данных графа для импорта"""

    horizons: list[ImportHorizon] = Field(..., description="Список горизонтов")
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Метаданные графа")


class ImportResultResponse(BaseModel):
    """Результат импорта графа"""

    success: bool = Field(..., description="Успешность импорта")
    message: str = Field(..., description="Сообщение о результате")
    created_horizons: int = Field(0, description="Создано горизонтов")
    created_nodes: int = Field(0, description="Создано узлов")
    created_edges: int = Field(0, description="Создано рёбер")
    created_tags: int = Field(0, description="Создано меток")
    horizon_ids: list[int] = Field(default_factory=list, description="ID созданных горизонтов")
    errors: list[str] = Field(default_factory=list, description="Ошибки при импорте")
