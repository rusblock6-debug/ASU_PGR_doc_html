"""
Конфигурация приложения с использованием Pydantic Settings.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Основные настройки приложения.
    """
    # FastAPI Configuration
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8002
    RELOAD: bool = False
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # MQTT Configuration
    NANOMQ_HOST: str = "nanomq-server"
    NANOMQ_MQTT_PORT: int = 1883  # Порт берется из переменной окружения NANOMQ_MQTT_PORT
    NANOMQ_WS_PORT: int = 8083  # Порт берется из переменной окружения NANOMQ_WS_PORT
    
    # Telemetry Storage Configuration
    TELEMETRY_STREAM_TTL_SECONDS: int = 7200  # 2 часа по умолчанию
    
    # Timezone
    TIMEZONE: str = "Europe/Moscow"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

