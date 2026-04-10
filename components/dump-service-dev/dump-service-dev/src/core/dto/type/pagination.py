# ruff: noqa: D100, D101

from pydantic import BaseModel


class PaginationParams(BaseModel):
    skip: int = 0
    limit: int = 100
