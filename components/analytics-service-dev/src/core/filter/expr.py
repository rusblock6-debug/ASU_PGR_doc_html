# ruff: noqa: E501
"""axiom.core.filter.expr — Filter expression types."""

from abc import ABC, abstractmethod
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from src.core.filter.type import FilterType, QueryOperator


class FilterExpr(BaseModel, ABC):
    """Base class for all filter nodes."""

    kind: str

    @abstractmethod
    def extract_filter_params(self) -> "list[FilterParam]":
        """Extract all filter parameters from the node."""

    def __and__(self, other: "FilterParam | FilterGroup") -> "FilterGroup":
        """Combine with another filter using AND operator."""
        return FilterGroup(type=FilterType.AND, items=[self, other])  # type: ignore[list-item]

    def __or__(self, other: "FilterParam | FilterGroup") -> "FilterGroup":
        """Combine with another filter using OR operator."""
        return FilterGroup(type=FilterType.OR, items=[self, other])  # type: ignore[list-item]


class FilterParam(FilterExpr):
    """Atomic filter condition."""

    kind: Literal["param"] = "param"
    field: str = Field(..., examples=["name"])
    value: Any = Field(..., examples=["abc"])
    operator: QueryOperator = Field(..., examples=[QueryOperator.EQUALS])

    def extract_filter_params(self) -> "list[FilterParam]":
        """Return this filter parameter as a single-element list."""
        return [self]

    def __repr__(self) -> str:
        """Return string representation of the filter parameter."""
        return (
            f"FilterParam(field={self.field!r}, value={self.value!r}, operator={self.operator!r})"
        )


class FilterGroup(FilterExpr):
    """Group of filter conditions with AND/OR operator."""

    kind: Literal["group"] = "group"
    type: FilterType = Field(..., examples=[FilterType.AND])
    items: list["FilterNode"] = Field(..., examples=[[]])

    def extract_filter_params(self) -> list[FilterParam]:
        """Recursively extract all filter parameters from child nodes."""
        params = []
        for item in self.items:
            params.extend(item.extract_filter_params())
        return params

    def __repr__(self) -> str:
        """Return string representation of the filter group."""
        items_repr = ", ".join(repr(item) for item in self.items)
        return f"FilterGroup(type={self.type!r}, items=[{items_repr}])"


FilterNode = Annotated[FilterParam | FilterGroup, Field(discriminator="kind")]


class FilterRequest(BaseModel):
    """Filter request with tree structure."""

    chain: FilterNode = Field(..., description="Root node of the filter tree")

    def extract_filter_params(self) -> list[FilterParam]:
        """Extract all filter parameters from the filter chain."""
        return self.chain.extract_filter_params()

    def __repr__(self) -> str:
        """Return string representation of the filter request."""
        return f"FilterRequest(chain={self.chain!r})"
