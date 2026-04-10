# ruff: noqa: D100, D101, D102
from typing import Any

from pydantic import BaseModel, Field

from src.core.dto.type.filter import FilterType
from src.core.dto.type.query import QueryOperator


class FilterParam(BaseModel):
    field: str = Field(..., examples=["message"])
    value: Any = Field(..., examples=["abc"])
    operator: QueryOperator = Field(..., examples=[QueryOperator.EQUALS])


class FilterRequest(BaseModel):
    filters: list[FilterParam] = Field([])
    type: FilterType = Field(FilterType.OR)

    def __repr__(self) -> str:
        """Представление данных схемы для ключа."""
        filters_repr = (
            "; ".join(f"{filter_param}" for filter_param in self.filters)
            if self.filters
            else "None"
        )
        return f"{self.__class__.__name__}(filters=[{filters_repr}], type={self.type})"
