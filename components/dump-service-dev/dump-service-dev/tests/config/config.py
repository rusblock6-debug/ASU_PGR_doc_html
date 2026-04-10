# ruff: noqa: S104
from pathlib import Path

from pydantic import Field

from src.core.config import Settings, project_path
from src.core.dto.type.app_mode import ModeType
from src.core.trip_service_config import TripServiceSettings
from src.core.util.project import ProjectInfo


class TestTripServiceSettings(TripServiceSettings):
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="password")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_DATABASE: str = Field(default="dump-service")


class TestSettings(Settings):
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    MODE: ModeType = Field(default=ModeType.production)

    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="password")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_DATABASE: str = Field(default="dump-service")

    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6754)
    REDIS_PASSWORD: str = Field(default="password")
    REDIS_CACHE_DATABASE: str = Field(default="0")

    S3_ACCESS_KEY: str = Field(default="S3_ACCESS_KEY")
    S3_SECRET_KEY: str = Field(default="S3_SECRET_KEY")
    S3_ENDPOINT_URL: str = Field(default="S3_ENDPOINT_URL")
    S3_REGION_NAME: str = Field(default="S3_REGION_NAME")

    DUMP_STORAGE_DIR: Path = Field(default_factory=lambda: project_path / "data")

    # mqtt / nanomq
    NANOMQ_HOST: str = Field(default="nanomq")
    NANOMQ_PORT: int = Field(default=12345)
    NANOMQ_KEEPALIVE: int = Field(default=60)

    TRUCK_ID: int = Field(default=4)

    # for db models
    EXCLUDE_FIELDS: list[str] = ["id", "created_at", "updated_at"]

    # path & url
    PROJECT_PATH: Path = project_path
    PROJECT_INFO: ProjectInfo = ProjectInfo(project_path.as_posix())

    # another
    TRIP_SERVICE_SETTINGS: TripServiceSettings = Field(default_factory=TestTripServiceSettings)
    EKIPER_SETTINGS: None = Field(None)

    # TEST config

    USE_EXTERNAL_DB: bool = False


settings = TestSettings()


def get_settings() -> TestSettings:
    """Return cached test settings instance."""
    return settings
