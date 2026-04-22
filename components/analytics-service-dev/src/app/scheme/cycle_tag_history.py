# ruff: noqa: D100, D101, D102
import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from src.core.filter.expr import FilterExpr
from src.core.filter.type import FilterType, QueryOperator


class CycleTagHistoryResponse(BaseModel):
    id: str = Field(..., examples=["abc-123"])
    timestamp: datetime.datetime = Field(..., examples=["2025-01-01T00:00:00"])
    vehicle_id: int = Field(..., examples=[123])
    cycle_id: str | None = Field(None, examples=["cycle-456"])
    place_id: int = Field(..., examples=[1])
    place_name: str = Field(..., examples=["Карьер-1"])
    place_type: str = Field(..., examples=["quarry"])
    tag_id: int = Field(..., examples=[10])
    tag_name: str = Field(..., examples=["Вход зона погрузки"])
    tag_event: str = Field(..., examples=["entry"])

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v: int | datetime.datetime) -> datetime.datetime:
        if isinstance(v, int):
            return datetime.datetime.fromtimestamp(v, tz=datetime.UTC)
        return v


class CycleTagHistoryField(StrEnum):
    """Допустимые поля для фильтрации."""

    id = "id"
    timestamp = "timestamp"
    vehicle_id = "vehicle_id"
    cycle_id = "cycle_id"
    place_id = "place_id"
    place_name = "place_name"
    place_type = "place_type"
    tag_id = "tag_id"
    tag_name = "tag_name"
    tag_event = "tag_event"


_FIELD_VALUE_TYPES: dict[CycleTagHistoryField, tuple[type, ...]] = {
    CycleTagHistoryField.id: (str,),
    CycleTagHistoryField.timestamp: (int, str),
    CycleTagHistoryField.vehicle_id: (int,),
    CycleTagHistoryField.cycle_id: (str,),
    CycleTagHistoryField.place_id: (int,),
    CycleTagHistoryField.place_name: (str,),
    CycleTagHistoryField.place_type: (str,),
    CycleTagHistoryField.tag_id: (int,),
    CycleTagHistoryField.tag_name: (str,),
    CycleTagHistoryField.tag_event: (str,),
}


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


class CycleTagHistoryFilterParam(FilterExpr):
    """Фильтр по конкретному полю cycle_tag_history."""

    kind: Literal["param"] = "param"
    field: CycleTagHistoryField = Field(
        ...,
        examples=[CycleTagHistoryField.vehicle_id],
    )
    value: str | int | float | list[str | int | float] | None = Field(
        ...,
        examples=[123, "entry"],
    )
    operator: QueryOperator = Field(..., examples=[QueryOperator.EQUALS])

    @field_validator("value", mode="before")
    @classmethod
    def check_value_type(cls, v: object, info: object) -> object:
        return v

    def extract_filter_params(self) -> list["CycleTagHistoryFilterParam"]:  # type: ignore[override]
        return [self]


class CycleTagHistoryFilterGroup(FilterExpr):
    """Группа фильтров с AND/OR."""

    kind: Literal["group"] = "group"
    type: FilterType = Field(..., examples=[FilterType.AND])
    items: list["CycleTagHistoryFilterNode"] = Field(...)

    def extract_filter_params(self) -> list[CycleTagHistoryFilterParam]:  # type: ignore[override]
        params = []
        for item in self.items:
            params.extend(item.extract_filter_params())
        return params


CycleTagHistoryFilterNode = Annotated[
    CycleTagHistoryFilterParam | CycleTagHistoryFilterGroup,
    Field(discriminator="kind"),
]

CycleTagHistoryFilterGroup.model_rebuild()


class CycleTagHistoryFilterRequest(BaseModel):
    """Запрос с деревом фильтров для cycle_tag_history."""

    chain: CycleTagHistoryFilterNode = Field(
        ...,
        description="Корень дерева фильтров",
    )

    def extract_filter_params(self) -> list[CycleTagHistoryFilterParam]:
        return self.chain.extract_filter_params()
