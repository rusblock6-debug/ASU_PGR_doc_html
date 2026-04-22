# ruff: noqa: D100, D101

from pydantic import BaseModel, Field


class ConfigS3(BaseModel):
    """Схема креденшианалов для работы с S3 хранилищем."""

    aws_access_key_id: str = Field(...)
    aws_secret_access_key: str = Field(...)
    endpoint_url: str = Field(...)
    region_name: str = Field(...)
    service_name: str = Field(...)
