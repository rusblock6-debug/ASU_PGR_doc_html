# ruff: noqa: D100, D101, D106
# mypy: disable-error-code="call-arg,valid-type,name-defined,type-arg"
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BaseModelWithTimestamp(BaseModel):
    created_at: datetime = Field(
        ...,
        examples=[datetime.now()],
        description="ISO-8601 timestamp",
    )
    updated_at: datetime = Field(
        ...,
        examples=[datetime.now()],
        description="ISO-8601 timestamp",
    )

    model_config = ConfigDict(from_attributes=True)
