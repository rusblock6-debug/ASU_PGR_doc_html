"""Analytics domain models and enums for platform_sdk.

All models are pure pydantic v2 — no HTTP or transport dependencies.

Filter tree
-----------
A filter is either a leaf condition (FilterParam) or a logical group
(FilterGroup) of nested filters. Both are generic over the field enum,
so the same shapes serve every resource:

    VehicleTelemetryFilter = (
        FilterParam[VehicleTelemetryField]
        | FilterGroup[VehicleTelemetryField]
    )
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Generic, Literal, TypeAlias, TypeVar

from pydantic import BaseModel, Field, model_validator

T = TypeVar("T")
TField = TypeVar("TField", bound=StrEnum)


class VehicleTelemetryField(StrEnum):
    """Fields available for filtering and sorting vehicle telemetry."""

    BORT = "bort"
    TIMESTAMP = "timestamp"
    LAT = "lat"
    LON = "lon"
    HEIGHT = "height"
    SPEED = "speed"
    FUEL = "fuel"


class CycleTagHistoryField(StrEnum):
    """Fields available for filtering and sorting cycle tag history."""

    ID = "id"
    TIMESTAMP = "timestamp"
    VEHICLE_ID = "vehicle_id"
    CYCLE_ID = "cycle_id"
    PLACE_ID = "place_id"
    PLACE_NAME = "place_name"
    PLACE_TYPE = "place_type"
    TAG_ID = "tag_id"
    TAG_NAME = "tag_name"
    TAG_EVENT = "tag_event"


class QueryOperator(StrEnum):
    """Comparison operators for filter conditions."""

    EQUALS = "EQUALS"
    NOT_EQUAL = "NOT_EQUAL"
    IN = "IN"
    NOT_IN = "NOT_IN"
    GREATER = "GREATER"
    EQUALS_OR_GREATER = "EQUALS_OR_GREATER"
    LESS = "LESS"
    EQUALS_OR_LESS = "EQUALS_OR_LESS"
    STARTS_WITH = "STARTS_WITH"
    NOT_START_WITH = "NOT_START_WITH"
    ENDS_WITH = "ENDS_WITH"
    NOT_END_WITH = "NOT_END_WITH"
    CONTAINS = "CONTAINS"
    NOT_CONTAIN = "NOT_CONTAIN"


_LIST_OPERATORS: frozenset[QueryOperator] = frozenset(
    {QueryOperator.IN, QueryOperator.NOT_IN},
)


class FilterType(StrEnum):
    """Logical connector for combining filter items in a FilterGroup."""

    AND = "AND"
    OR = "OR"


class SortDirection(StrEnum):
    """Sort direction for query results."""

    ASC = "asc"
    DESC = "desc"


Scalar: TypeAlias = str | int | float
FilterValue: TypeAlias = Scalar | list[Scalar] | None


class FilterParam(BaseModel, Generic[TField]):
    """Leaf filter condition: a single field comparison.

    The kind discriminator is set automatically — it exists for the
    pydantic discriminated union and is not part of user input semantics.
    """

    kind: Literal["param"] = "param"
    field: TField
    value: FilterValue
    operator: QueryOperator

    @model_validator(mode="after")
    def _check_value_matches_operator(self) -> FilterParam[TField]:
        is_list = isinstance(self.value, list)
        if self.operator in _LIST_OPERATORS and not is_list:
            raise ValueError(
                f"operator {self.operator.value} requires a list value, got {type(self.value).__name__}",
            )
        if self.operator not in _LIST_OPERATORS and is_list:
            raise ValueError(
                f"operator {self.operator.value} does not accept a list value",
            )
        return self


class FilterGroup(BaseModel, Generic[TField]):
    """Composite filter: AND/OR group of FilterParam or nested FilterGroup."""

    kind: Literal["group"] = "group"
    type: FilterType
    items: list[
        Annotated[
            FilterParam[TField] | FilterGroup[TField],
            Field(discriminator="kind"),
        ]
    ]


VehicleTelemetryFilter: TypeAlias = (
    FilterParam[VehicleTelemetryField] | FilterGroup[VehicleTelemetryField]
)
CycleTagHistoryFilter: TypeAlias = (
    FilterParam[CycleTagHistoryField] | FilterGroup[CycleTagHistoryField]
)


class VehicleTelemetryResponse(BaseModel):
    """Single vehicle telemetry record returned by the analytics service.

    Required fields: bort, timestamp, lat, lon.
    Optional fields: height, speed, fuel — default to None when not recorded.
    """

    bort: int
    timestamp: datetime
    lat: float
    lon: float
    height: float | None = None
    speed: float | None = None
    fuel: float | None = None


class CycleTagHistoryResponse(BaseModel):
    """Single cycle_tag_history record returned by the trip service.

    cycle_id is nullable — all other fields are required.
    """

    id: str
    timestamp: datetime
    vehicle_id: int
    cycle_id: str | None = None
    place_id: int
    place_name: str
    place_type: str
    tag_id: int
    tag_name: str
    tag_event: str


class PaginationResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    page: int
    page_size: int
    total_pages: int
    total_count: int
    data: list[T]


__all__ = [
    "CycleTagHistoryField",
    "CycleTagHistoryFilter",
    "CycleTagHistoryResponse",
    "FilterGroup",
    "FilterParam",
    "FilterType",
    "FilterValue",
    "PaginationResponse",
    "QueryOperator",
    "SortDirection",
    "VehicleTelemetryField",
    "VehicleTelemetryFilter",
    "VehicleTelemetryResponse",
]
