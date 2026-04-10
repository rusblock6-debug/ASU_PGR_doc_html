# ruff: noqa: D100, D101, D106
# mypy: disable-error-code="call-arg,valid-type,name-defined,type-arg"

from pydantic import BaseModel, ConfigDict, Field


class PaginationResponse[T](BaseModel):
    page: int = Field(..., examples=[0])
    page_size: int = Field(..., examples=[0])
    total_pages: int = Field(..., examples=[0])
    total_count: int = Field(..., examples=[0])
    data: list[T] = Field(...)

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
