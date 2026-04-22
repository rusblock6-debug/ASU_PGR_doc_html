# ruff: noqa: D100, D101, D102
import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.filter.expr import FilterExpr
from src.core.filter.type import FilterType, QueryOperator


class VehicleTelemetryResponse(BaseModel):
    bort: int = Field(..., examples=[123])
    timestamp: datetime.datetime = Field(..., examples=["2025-01-01T00:00:00"])
    lat: float = Field(..., examples=[56.838])
    lon: float = Field(..., examples=[60.603])
    height: float | None = Field(None, examples=[250.0])
    speed: float | None = Field(None, examples=[45.5])
    fuel: float | None = Field(None, examples=[78.2])

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v: int | datetime.datetime) -> datetime.datetime:
        if isinstance(v, int):
            return datetime.datetime.fromtimestamp(v, tz=datetime.UTC)
        return v


class VehicleTelemetryField(StrEnum):
    """Допустимые поля для фильтрации."""

    bort = "bort"  # int
    timestamp = "timestamp"  # int (unix)
    lat = "lat"  # float
    lon = "lon"  # float
    height = "height"  # float | null
    speed = "speed"  # float | null
    fuel = "fuel"  # float | null


_FIELD_VALUE_TYPES: dict[VehicleTelemetryField, tuple[type, ...]] = {
    VehicleTelemetryField.bort: (int,),
    VehicleTelemetryField.timestamp: (int, str),
    VehicleTelemetryField.lat: (int, float),
    VehicleTelemetryField.lon: (int, float),
    VehicleTelemetryField.height: (int, float),
    VehicleTelemetryField.speed: (int, float),
    VehicleTelemetryField.fuel: (int, float),
}

_FIELD_TYPE_DESCRIPTION = (
    "bort: int, "
    "timestamp: int (unix epoch) или str (ISO 8601, например '2025-04-07T08:00:00'), "
    "lat: float, lon: float, "
    "height: float | null, speed: float | null, fuel: float | null"
)


def _parse_datetime_to_unix(value: str) -> int:
    """Парсит ISO 8601 строку в unix timestamp (UTC)."""
    try:
        dt = datetime.datetime.fromisoformat(value)
    except ValueError:
        msg = f"Invalid datetime format: {value!r}. Expected ISO 8601, e.g. '2025-04-07T08:00:00'"
        raise ValueError(msg) from None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.UTC)
    return int(dt.timestamp())


class VehicleTelemetryFilterParam(FilterExpr):
    """Фильтр по конкретному полю vehicle_telemetry."""

    kind: Literal["param"] = "param"
    field: VehicleTelemetryField = Field(
        ...,
        description=f"Поле для фильтрации. Типы значений: {_FIELD_TYPE_DESCRIPTION}",
        examples=[VehicleTelemetryField.bort],
    )
    value: str | int | float | list[str | int | float] | None = Field(
        ...,
        description="Значение фильтра. Тип зависит от поля.",
        examples=[17, 1700000000, 56.8],
    )
    operator: QueryOperator = Field(..., examples=[QueryOperator.EQUALS])

    @model_validator(mode="after")
    def check_value_type(self) -> "VehicleTelemetryFilterParam":
        # Для timestamp: конвертируем ISO-строку в unix int
        if self.field == VehicleTelemetryField.timestamp and isinstance(self.value, str):
            self.value = _parse_datetime_to_unix(self.value)
            return self

        allowed = _FIELD_VALUE_TYPES.get(self.field)
        if allowed is None:
            return self
        values = self.value if isinstance(self.value, list) else [self.value]  # type: ignore[list-item]
        for v in values:
            if v is not None and not isinstance(v, allowed):
                expected = " | ".join(t.__name__ for t in allowed)
                msg = f"Field '{self.field}' expects {expected}, got {type(v).__name__}: {v!r}"
                raise ValueError(msg)
        return self

    def extract_filter_params(self) -> list["VehicleTelemetryFilterParam"]:  # type: ignore[override]
        return [self]


class VehicleTelemetryFilterGroup(FilterExpr):
    """Группа фильтров с AND/OR."""

    kind: Literal["group"] = "group"
    type: FilterType = Field(..., examples=[FilterType.AND])
    items: list["VehicleTelemetryFilterNode"] = Field(...)

    def extract_filter_params(self) -> list[VehicleTelemetryFilterParam]:  # type: ignore[override]
        params = []
        for item in self.items:
            params.extend(item.extract_filter_params())
        return params


VehicleTelemetryFilterNode = Annotated[
    VehicleTelemetryFilterParam | VehicleTelemetryFilterGroup,
    Field(discriminator="kind"),
]

# Rebuild нужен из-за forward ref на VehicleTelemetryFilterNode
VehicleTelemetryFilterGroup.model_rebuild()


class VehicleTelemetryFilterRequest(BaseModel):
    """Запрос с деревом фильтров для vehicle_telemetry."""

    chain: VehicleTelemetryFilterNode = Field(
        ...,
        description="Корень дерева фильтров",
    )

    def extract_filter_params(self) -> list[VehicleTelemetryFilterParam]:
        return self.chain.extract_filter_params()
