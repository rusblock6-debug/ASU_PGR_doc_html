"""Конфигурация приложения с использованием Pydantic Settings."""

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class APIClientUrlConfig(BaseModel):
    """Конфигурация URL API клиента."""

    base_graph_service_url: str = "http://graph-service-backend:5000/api/"
    place: str = "places/"


class Settings(BaseSettings):
    """Основные настройки приложения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
    )

    # FastAPI Configuration
    DEBUG: bool = True
    HOST: str = "0.0.0.0"  # noqa: S104
    PORT: int = 8001
    RELOAD: bool = True

    # Deployment mode
    DEPLOYMENT_MODE: str = Field(
        default="server",
        description="Deployment mode: server or board",
    )

    # Sync configuration (board → server)
    SERVER_SYNC_BASE_URL: str | None = Field(
        default=None,
        description="Base URL of the server enterprise-service instance used for board sync",
    )
    SYNC_EXPORT_PATH: str = Field(
        default="/api/sync/full",
        description="Server endpoint path that returns a full data snapshot for sync",
    )
    SYNC_ON_START: bool = Field(
        default=True,
        description="Run full sync automatically on startup when DEPLOYMENT_MODE=board",
    )
    SYNC_HTTP_TIMEOUT: int = Field(
        default=30,
        description="Timeout (seconds) for sync HTTP requests",
    )

    # Database Configuration
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    DATABASE_ECHO: bool = False

    # Nanomq (локальный MQTT брокер)
    NANOMQ_HOST: str = Field(default="nanomq-server", description="Nanomq host")
    NANOMQ_PORT: int = Field(default=1883, description="Nanomq MQTT port")

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"

    # Timezone
    TIMEZONE: str = "Europe/Moscow"

    # Logging
    LOG_LEVEL: str = "INFO"

    api_client: APIClientUrlConfig = APIClientUrlConfig()


settings = Settings()  # type: ignore[call-arg]
