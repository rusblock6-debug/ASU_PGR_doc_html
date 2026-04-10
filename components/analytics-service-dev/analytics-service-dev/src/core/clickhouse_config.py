# ruff: noqa: D100, D101
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClickHouseSettings(BaseSettings):
    HOST: str = Field(...)
    PORT: int = Field(...)
    USERNAME: str = Field(...)
    PASSWORD: str = Field(...)
    DATABASE: str = Field(...)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="CLICKHOUSE_",
    )
