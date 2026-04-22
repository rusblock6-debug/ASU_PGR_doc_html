# ruff: noqa: D100, D101, D102

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AmqpDsn, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.clickhouse_config import ClickHouseSettings
from src.core.dto.type.app_mode import ModeType
from src.core.util.project import ProjectInfo

project_path: Path = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent


class Settings(BaseSettings):
    # from .env
    HOST: str = Field(...)
    PORT: int = Field(...)
    MODE: ModeType = Field(default=ModeType.dev)

    S3_ACCESS_KEY: str = Field(...)
    S3_SECRET_KEY: str = Field(...)
    S3_ENDPOINT_URL: str = Field(...)
    S3_REGION_NAME: str = Field(...)
    S3_BUCKET_NAME: str = Field(default="dump-service")

    RABBIT_USER: str = Field(...)
    RABBIT_PASSWORD: str = Field(...)
    RABBIT_HOST: str = Field(...)
    RABBIT_PORT: int = Field(...)

    # for db models
    EXCLUDE_FIELDS: list[str] = ["id", "created_at", "updated_at"]

    # path & url
    PROJECT_PATH: Path = project_path
    PROJECT_INFO: ProjectInfo = ProjectInfo(project_path.as_posix())

    # additional services settings

    clickhouse_settings: ClickHouseSettings = ClickHouseSettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    @property
    def RABBIT_URL(self) -> str:
        return AmqpDsn.build(
            scheme="amqp",
            username=self.RABBIT_USER,
            password=self.RABBIT_PASSWORD,
            host=self.RABBIT_HOST,
            port=self.RABBIT_PORT,
        ).unicode_string()


@lru_cache
def get_settings() -> Settings:
    """Get settings."""
    return Settings()
