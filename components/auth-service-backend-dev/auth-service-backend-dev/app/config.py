import os
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'your-secret-key')  # Change in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', 7)
    ALGORITHM: str = os.getenv('ALGORITHM', "HS256")
    POSTGRES_USER: str = os.getenv('POSTGRES_USER', "postgres")
    POSTGRES_PASSWORD: str = os.getenv('POSTGRES_PASSWORD', "postgres")
    POSTGRES_DB: str = os.getenv('POSTGRES_DB', "dispatching_auth")
    POSTGRES_HOST: str = os.getenv('POSTGRES_HOST', "localhost")
    DATABASE_URL: str = os.getenv('DATABASE_URL', "postgresql+asyncpg://postgres:postgres@localhost:5432/dispatching_auth")
    MODE: str = os.getenv('MODE', "BORT")
    ENCRYPTION_KEY: str = os.getenv('ENCRYPTION_KEY', 'PMZmElN7bnsxfqtfzFL-3u6mfAnQfu1DRwOzWkfDnvU=')
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://redis:6380/0')

    class Config:
        env_file = ".env"

    def get_bort_available_requests(self):
        return {
            # Auth rotes
            "/auth/login": "POST",
            "/auth/refresh": "POST",
            "/auth/logout": "POST",
            "/auth/verify": "POST",

            # Permissions routes
            "/auth/permissions/check": "POST",
            "/auth/permissions/my": "GET",

            # Users routes
            "/auth/me": "GET",

            # Staff routes
            "/auth/staff": "GET",
        }

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
