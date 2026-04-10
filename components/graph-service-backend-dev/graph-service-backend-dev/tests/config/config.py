# ruff: noqa: S104
from pydantic import Field

from config.settings import Settings


class TestSettings(Settings):
    s3_access_key: str = Field(default="login", description="s3 login")
    s3_secret_key: str = Field(default="password", description="s3 password")


settings = TestSettings()


def get_settings() -> TestSettings:
    """Return cached test settings instance."""
    return settings
