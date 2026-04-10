"""Gateway configuration models and settings loader."""

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import AnyHttpUrl, BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ALLOWED_PATH_PLACEHOLDERS = {"version", "path"}
_PATH_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


class ServiceSettings(BaseModel):
    """Service upstream configuration."""

    url: AnyHttpUrl
    path_pattern: str = "/api/{version}/{path}"

    @field_validator("path_pattern")
    @classmethod
    def validate_path_pattern(cls, value: str) -> str:
        """Ensure path pattern has a leading slash and supported placeholders."""
        if not value.startswith("/"):
            raise ValueError("path_pattern must start with '/'")

        placeholders = _PATH_PLACEHOLDER_RE.findall(value)
        invalid_placeholders = sorted(
            {
                placeholder
                for placeholder in placeholders
                if placeholder not in _ALLOWED_PATH_PLACEHOLDERS
            },
        )
        if invalid_placeholders:
            invalid_tokens = ", ".join(f"{{{placeholder}}}" for placeholder in invalid_placeholders)
            raise ValueError(
                f"path_pattern contains unsupported placeholders: {invalid_tokens}",
            )

        return value


class AuthSettings(BaseModel):
    """Auth service configuration."""

    url: AnyHttpUrl
    verify_endpoint: str = "/api/v1/verify"


class Settings(BaseSettings):
    """Application settings loaded from config.yaml and environment."""

    services: dict[str, ServiceSettings]
    auth: AuthSettings
    service_name: str = "api-gateway"
    environment: str | None = None
    log_level: str = "INFO"
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8080
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    @classmethod
    def settings_customise_sources(  # type: ignore[no-untyped-def]  # noqa: D102
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        def yaml_config_settings_source():  # type: ignore[no-untyped-def]
            config_path = Path("config.yaml")
            if not config_path.exists():
                return {}
            with open(config_path) as f:
                return yaml.safe_load(f) or {}

        return (
            init_settings,
            yaml_config_settings_source,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )
