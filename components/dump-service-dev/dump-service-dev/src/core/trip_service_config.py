# ruff: noqa: D100, D101, D102
from typing import Any

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class TripServiceSettings(BaseSettings):
    POSTGRES_USER: str = Field(...)
    POSTGRES_PASSWORD: str = Field(...)
    POSTGRES_PORT: int = Field(...)
    POSTGRES_HOST: str = Field(...)
    POSTGRES_DATABASE: str = Field(...)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="TRIP_SERVICE_",
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    @property
    def POSTGRES_URL(self) -> str:
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=f"{self.POSTGRES_DATABASE}",
        ).unicode_string()
