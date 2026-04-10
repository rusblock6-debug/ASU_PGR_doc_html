import os
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    VAULT_TOKEN: str = os.getenv('VAULT_TOKEN', 'root')
    BASE_URL: str = os.getenv('VAULT_URL', 'http://localhost:8200')
    TEMPLATE_FILE_PATH: str = os.getenv('TEMPLATE_FILE_PATH', '.env_bort_template')


@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
