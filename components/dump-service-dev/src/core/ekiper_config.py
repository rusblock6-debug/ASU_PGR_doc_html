# ruff: noqa: D100, D101, D102
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class EkiperSettings(BaseSettings):
    FLUSH_SECONDS_INTERVAL: int = 100
    BATCH_SIZE: int = 1000
    FILE_ROTATE_SIZE: str = "50KB"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="EKIPER_",
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
