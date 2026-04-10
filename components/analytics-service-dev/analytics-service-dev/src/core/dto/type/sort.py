# ruff: noqa: D100, D101
from enum import StrEnum

from pydantic import BaseModel, Field


class SortTypeEnum(StrEnum):
    asc = "asc"
    desc = "desc"


class SortParams(BaseModel):
    sort_by: str | None = Field(None, examples=["id"])
    sort_type: SortTypeEnum | None = Field(None, examples=["asc", "desc"])
