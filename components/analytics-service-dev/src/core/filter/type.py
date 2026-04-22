"""axiom.core.filter.type — Filter enums and sort params."""

from enum import StrEnum

from pydantic import BaseModel, Field


class FilterType(StrEnum):
    """Logical operator used to combine multiple filter conditions."""

    AND = "AND"
    OR = "OR"


class QueryOperator(StrEnum):
    """Comparison operator applied to a single filter field."""

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


class SortTypeEnum(StrEnum):
    """Sort direction for query ordering."""

    asc = "asc"
    desc = "desc"


class SortParams(BaseModel):
    """Query parameters for controlling sort order."""

    sort_by: str | None = Field(None, examples=["id"])
    sort_type: SortTypeEnum | None = Field(None, examples=["asc", "desc"])
