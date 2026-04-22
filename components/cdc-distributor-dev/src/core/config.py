"""Конфигурация приложения через pydantic-settings."""

from typing import Annotated

from pydantic import BeforeValidator, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseServiceSettings(BaseSettings):
    """Base class for database service settings."""

    POSTGRES_HOST: str | None = None
    POSTGRES_PORT: int | None = None
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_DATABASE: str | None = None

    @property
    def POSTGRES_URL(self) -> str | None:
        """Формирует URL подключения к PostgreSQL."""
        if self.POSTGRES_HOST is None:
            return None
        return PostgresDsn.build(
            scheme="postgresql",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=f"{self.POSTGRES_DATABASE}",
        ).unicode_string()


class DistributorServiceSettings(DatabaseServiceSettings):
    """Distributor service database settings for per-bort offset tracking."""

    pass


def _parse_int_list(v: str | int | list[int]) -> list[int]:
    """Парсит comma-separated строку, int или list[int] в list[int]."""
    if isinstance(v, list):
        return v
    if isinstance(v, int):
        return [v]
    if isinstance(v, str):
        return [int(x.strip()) for x in v.split(",") if x.strip()]
    raise ValueError(f"Cannot parse {v!r} as list[int]")


class RetrySettings(BaseSettings):
    """Настройки retry с exponential backoff."""

    MAX_RETRIES: int = Field(default=5)
    INITIAL_DELAY: float = Field(default=1.0)
    MAX_DELAY: float = Field(default=60.0)
    EXPONENTIAL_BASE: float = Field(default=2.0)
    JITTER: bool = Field(default=True)


class Settings(BaseSettings):
    """Основные настройки приложения."""

    # Настройки для подключения к стриму RabbitMQ
    RABBIT_HOST: str = Field(...)
    RABBIT_PORT: int = Field(...)
    RABBIT_USER: str = Field(...)
    RABBIT_PASSWORD: str = Field(...)
    RABBIT_VHOST: str = "/"

    # Настройки для подключения к очереди RabbitMQ
    RABBIT_AMQP_HOST: str = Field(...)
    RABBIT_AMQP_PORT: int = Field(...)
    RABBIT_AMQP_USER: str = Field(...)
    RABBIT_AMQP_PASSWORD: str = Field(...)

    retry: RetrySettings = RetrySettings()

    # Per-bort fan-out config
    BORT_IDS: Annotated[list[int], BeforeValidator(_parse_int_list)] = []

    # Distributor DB for BortOffsetManager
    distributor: DistributorServiceSettings = DistributorServiceSettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )


settings = Settings()  # type: ignore[call-arg]
