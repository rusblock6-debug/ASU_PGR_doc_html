# ruff: noqa: D100, D101

from pydantic import BaseModel, Field


class CountResponse(BaseModel):
    count: int = Field(..., examples=[100])
