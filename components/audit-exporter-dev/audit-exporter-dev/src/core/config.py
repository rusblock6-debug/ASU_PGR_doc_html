"""Typed runtime configuration for bootstrap dependencies."""

from enum import StrEnum
from typing import Final, Self
from urllib.parse import quote

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SourceName(StrEnum):
    """Fixed PostgreSQL source identifiers supported by the service."""

    graph = "graph"
    enterprise = "enterprise"
    trip = "trip"


SOURCE_NAMES: Final[tuple[SourceName, ...]] = tuple(SourceName)


class RedactedDsn(BaseModel):
    """Display-safe DSN variants for diagnostics and operator-facing output."""

    full: str
    without_credentials: str


def _strip_required(value: str) -> str:
    """Reject blank values after trimming surrounding whitespace."""
    stripped = value.strip()
    if not stripped:
        raise ValueError("value must not be blank")
    return stripped


class PostgresSourceSettings(BaseSettings):
    """Connection settings for one PostgreSQL source.

    Use ``for_source`` to create an instance that reads env vars
    with the prefix ``{NAME}__POSTGRES_`` (e.g. ``SAP__POSTGRES_HOST``).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    name: SourceName
    host: str = Field(min_length=1)
    port: int = Field(default=5432, ge=1, le=65535)
    database: str = Field(min_length=1)
    user: str = Field(min_length=1)
    password: str = Field(min_length=1)
    connect_timeout_seconds: float = Field(default=5.0, gt=0)

    @field_validator("host", "database", "user", "password")
    @classmethod
    def strip_required(cls, value: str) -> str:
        return _strip_required(value)

    @classmethod
    def for_source(cls, source: SourceName, **overrides: object) -> "PostgresSourceSettings":
        """Build settings for *source*, reading ``{SOURCE}__POSTGRES_*`` env vars."""

        class _Scoped(cls):  # type: ignore[misc,valid-type]
            model_config = SettingsConfigDict(
                env_prefix=f"{source.upper()}__POSTGRES_",
                env_file=".env",
                env_file_encoding="utf-8",
                case_sensitive=False,
                extra="ignore",
            )

        return _Scoped(name=source, **overrides)  # type: ignore[return-value]

    def async_sqlalchemy_dsn(self) -> str:
        """Return an async SQLAlchemy DSN with URL-encoded credentials."""
        return (
            "postgresql+asyncpg://"
            f"{quote(self.user)}:{quote(self.password)}@{self.host}:{self.port}/{self.database}"
        )

    def probe_dsn(self) -> RedactedDsn:
        """Return password-safe DSN renderings for diagnostics."""
        return RedactedDsn(
            full=(f"postgresql://{quote(self.user)}:***@{self.host}:{self.port}/{self.database}"),
            without_credentials=f"postgresql://{self.host}:{self.port}/{self.database}",
        )


class ClickHouseSettings(BaseModel):
    """Connection settings for the ClickHouse target."""

    host: str = Field(min_length=1)
    port: int = Field(default=8443, ge=1, le=65535)
    database: str = Field(min_length=1)
    user: str = Field(min_length=1)
    password: str = Field(min_length=1)
    secure: bool = True
    connect_timeout_seconds: float = Field(default=5.0, gt=0)

    @field_validator("host", "database", "user", "password")
    @classmethod
    def strip_required(cls, value: str) -> str:
        return _strip_required(value)

    def client_kwargs(self) -> dict[str, object]:
        """Return kwargs for clickhouse_connect client creation."""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.user,
            "password": self.password,
            "secure": self.secure,
            "connect_timeout": self.connect_timeout_seconds,
        }

    def probe_dsn(self) -> RedactedDsn:
        """Return password-safe ClickHouse DSN renderings for diagnostics."""
        scheme = "clickhouses" if self.secure else "clickhouse"
        return RedactedDsn(
            full=(f"{scheme}://{quote(self.user)}:***@{self.host}:{self.port}/{self.database}"),
            without_credentials=f"{scheme}://{self.host}:{self.port}/{self.database}",
        )


class AppSettings(BaseSettings):
    """Environment-backed runtime settings for the exporter service shell."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    clickhouse_host: str
    clickhouse_port: int = 8443
    clickhouse_database: str
    clickhouse_user: str
    clickhouse_password: str
    clickhouse_secure: bool = True

    log_level: str = Field(default="INFO")

    dependency_connect_timeout_seconds: float = Field(default=5.0, gt=0)
    source_poll_batch_size: int = Field(default=500, ge=1)
    source_poll_interval_seconds: float = Field(default=10.0, gt=0)

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        """Ensure nested models normalize cleanly during settings construction."""
        self.postgres_sources()
        self.clickhouse()
        return self

    def postgres_sources(self) -> dict[SourceName, PostgresSourceSettings]:
        """Build normalized source settings for the fixed PostgreSQL source list."""
        return {
            name: PostgresSourceSettings.for_source(
                name,
                connect_timeout_seconds=self.dependency_connect_timeout_seconds,
            )
            for name in SOURCE_NAMES
        }

    def clickhouse(self) -> ClickHouseSettings:
        """Build normalized ClickHouse target settings."""
        return ClickHouseSettings(
            host=self.clickhouse_host,
            port=self.clickhouse_port,
            database=self.clickhouse_database,
            user=self.clickhouse_user,
            password=self.clickhouse_password,
            secure=self.clickhouse_secure,
            connect_timeout_seconds=self.dependency_connect_timeout_seconds,
        )


def get_settings() -> AppSettings:
    """Load and validate application settings from the environment."""
    return AppSettings()  # type: ignore[call-arg]


def format_settings_validation_error(error: ValidationError) -> str:
    """Build a concise, user-facing validation error summary."""
    parts: list[str] = []
    for item in error.errors():
        location = ".".join(str(segment) for segment in item["loc"])
        parts.append(f"{location}: {item['msg']}")
    return "; ".join(parts)
