"""Конфигурация приложения через Pydantic Settings."""

from typing import Self

from pydantic import AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.enums.config import ServiceModeEnum


class RabbitMQSettings(BaseSettings):
    """Настройки подключения к RabbitMQ."""

    host: str = "localhost"
    port: int = 5672
    user: str = ""
    password: str = ""
    url: str = ""
    handler_delay: int = 60

    # настройка retry механизма
    retry_max_attempts: int = 5
    retry_base_delay_sec: float = 1.0

    @model_validator(mode="after")
    def generate_rabbitmq_url(self) -> Self:
        """Сформировать URL подключения к RabbitMQ."""
        self.url = f"amqp://{self.user}:{self.password}@{self.host}:{self.port}/"
        return self


class Settings(BaseSettings):
    """Настройки приложения Trip Service."""

    rabbit: RabbitMQSettings = RabbitMQSettings()

    # Core Configuration
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Log level")
    host: str = Field(default="0.0.0.0", description="Server host")  # noqa: S104
    port: int = Field(default=8000, description="Server port")
    timezone: str = Field(default="Europe/Moscow", description="Таймзона для отображения дат")

    # PostgreSQL + TimescaleDB
    postgres_host: str = Field(default="postgres", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="trip_service", description="Database name")
    postgres_user: str = Field(default="postgres", description="PostgreSQL user")
    postgres_password: str = Field(default="postgres", description="PostgreSQL password")

    # Redis
    redis_host: str = Field(default="redis", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")

    # Nanomq (локальный MQTT брокер)
    nanomq_host: str = Field(default="nanomq", description="Nanomq host")
    nanomq_port: int = Field(default=1883, description="Nanomq MQTT port")

    # Enterprise Service (для HTTP GET запросов в Bort Mode)
    # Bort Mode: после получения MQTT события от enterprise-service, делает HTTP GET
    # для получения полных данных shift_task, затем вызывает локальный API trip-service
    # Бортовой режим: обращаемся к локальному enterprise-service (enterprise-service:8001)
    # Серверный режим: можно переопределить через переменные окружения
    enterprise_service_host: str = Field(default="enterprise-service", description="Board enterprise Service host")
    enterprise_service_port: int = Field(default=8002, description="Board enterprise Service port")
    enterprise_vehicle_info_path: str = Field(
        default="/api/vehicles/{vehicle_id}",
        description="Путь (template) в enterprise-service для получения данных о машине",
    )
    enterprise_model_info_path: str = Field(
        default="/api/vehicle-models/{model_id}",
        description="Путь (template) в enterprise-service для получения данных о модели машины",
    )

    enterprise_http_timeout_seconds: float = Field(
        default=5.0,
        description="Таймаут HTTP запросов в enterprise-service/graph-service (секунды)",
    )

    # Graph Service (для получения данных о точках)
    graph_service_host: str = Field(default="graph-service-backend", description="Graph Service host")
    graph_service_port: int = Field(default=5000, description="Graph Service port")
    fleet_route_length_cache_ttl_seconds: float = Field(
        default=600.0,
        description="TTL кэша длины маршрута (сек) в fleet-control, ключ (place_a_id, place_b_id)",
    )

    # Trip Service
    vehicle_id: str = Field(default="4", description="ID транспорта: число для bort, '+' для server")
    end_cycle_weight: int = Field(
        default=10,
        description="Значение при котором для данной единицы техники заканчивается цикл",
    )
    service_mode: ServiceModeEnum = Field(
        default=ServiceModeEnum.bort,
        description="Режим работы сервиса: 'bort' или 'server'",
    )

    shift_auto_switch: bool = Field(
        default=True,
        description="Выключатель для автоматического переключения смены",
    )
    auto_approve_dispatcher_assignment_delay_seconds: int = Field(
        default=1,
        description=(
            "Задержка в секундах перед авто-подтверждением dispatcher assignment "
            "в server-режиме. 0 отключает авто-подтверждение."
        ),
    )

    analytics_service_host: str = Field(
        default="analytics-service",
        description="Analytics service host",
    )
    analytics_service_port: int = Field(
        default=8000,
        description="Analytics service host port",
    )

    @field_validator("service_mode")
    @classmethod
    def validate_service_mode(cls, v: str) -> str:
        """Проверить корректность режима работы сервиса."""
        if v not in ServiceModeEnum.modes():
            raise ValueError("service_mode должен быть 'bort' или 'server'")
        return v

    @field_validator("vehicle_id", mode="before")
    @classmethod
    def validate_vehicle_id(cls, v: object) -> str:
        """Для bort-режима требуется числовой vehicle_id.

        Для server-режима допускается '+' (wildcard).
        """
        if v is None:
            return "4"

        if isinstance(v, str):
            v = v.strip()
            if v.isdigit() or v == "+":
                return v
        raise ValueError("vehicle_id должен быть числом или '+' в server-режиме")

    @property
    def database_url(self) -> str:
        """Формирование Database URL для async SQLAlchemy."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """Формирование Redis URL."""
        return f"redis://{self.redis_host}:{self.redis_port}"

    @property
    def enterprise_service_url(self) -> str:
        """Базовый URL enterprise-service."""
        return f"http://{self.enterprise_service_host}:{self.enterprise_service_port}"

    @property
    def graph_service_url(self) -> str:
        """Базовый URL graph-service."""
        return f"http://{self.graph_service_host}:{self.graph_service_port}"

    @property
    def analytics_service_url(self) -> AnyHttpUrl:
        """URL analytics-service."""
        return AnyHttpUrl(f"http://{self.analytics_service_host}:{self.analytics_service_port}")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
    )


# Глобальный экземпляр настроек
settings = Settings()
