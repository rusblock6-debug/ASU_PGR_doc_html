import os
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache

SQLITE_DATABASE_URL = "sqlite+aiosqlite:///./data/settings_bort.db"


class Settings(BaseSettings):
    SETTINGS_URL: str = os.getenv('SETTINGS_URL', 'http://host.docker.internal:8006')
    ENTERPRISE_SERVER_URL: str = os.getenv('ENTERPRISE_SERVER_URL', 'http://host.docker.internal:8002')
    DATABASE_URL: str = Field(
        default=SQLITE_DATABASE_URL,
        validation_alias="SETTINGS_BORT_DATABASE_URL",
    )
    BORT_ENV_OUTPUT_PATH: str = os.getenv('BORT_ENV_OUTPUT_PATH', '')


@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
