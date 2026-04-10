# ruff: noqa: D100, D101, D102

import os
from pathlib import Path
from typing import Any

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.dto.type.app_mode import ModeType
from src.core.ekiper_config import EkiperSettings
from src.core.trip_service_config import TripServiceSettings
from src.core.util.project import ProjectInfo

project_path: Path = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent


class Settings(BaseSettings):
    # from .env
    HOST: str = Field(...)
    PORT: int = Field(...)
    MODE: ModeType = Field(default=ModeType.dev)

    POSTGRES_USER: str = Field(...)
    POSTGRES_PASSWORD: str = Field(...)
    POSTGRES_PORT: int = Field(...)
    POSTGRES_HOST: str = Field(...)
    POSTGRES_DATABASE: str = Field(...)

    REDIS_HOST: str = Field(...)
    REDIS_PORT: int = Field(...)
    REDIS_PASSWORD: str = Field(...)
    REDIS_CACHE_DATABASE: str = Field(...)

    S3_ACCESS_KEY: str = Field(...)
    S3_SECRET_KEY: str = Field(...)
    S3_ENDPOINT_URL: str = Field(...)
    S3_REGION_NAME: str = Field(...)

    DUMP_STORAGE_DIR: Path = Field(default_factory=lambda: project_path / "data")

    # mqtt / nanomq
    NANOMQ_HOST: str = Field(...)
    NANOMQ_PORT: int = Field(...)
    NANOMQ_KEEPALIVE: int = Field(default=60)

    TRUCK_ID: int = Field(...)
    WIFI_STATUS: bool = True

    # for db models
    EXCLUDE_FIELDS: list[str] = ["id", "created_at", "updated_at"]

    # path & url
    PROJECT_PATH: Path = project_path
    PROJECT_INFO: ProjectInfo = ProjectInfo(project_path.as_posix())

    # additional services settings

    TRIP_SERVICE_SETTINGS: TripServiceSettings = Field(default_factory=TripServiceSettings)
    EKIPER_SETTINGS: EkiperSettings = Field(default_factory=EkiperSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
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

    @property
    def REDIS_CACHE_URL(self) -> str:
        return RedisDsn.build(
            scheme="redis",
            password=self.REDIS_PASSWORD,
            host=self.REDIS_HOST,
            port=self.REDIS_PORT,
            path=self.REDIS_CACHE_DATABASE,
        ).unicode_string()

    @property
    def REDIS_URL(self) -> str:
        return self.REDIS_CACHE_URL


def get_settings() -> Settings:
    """Get settings."""
    return Settings()
