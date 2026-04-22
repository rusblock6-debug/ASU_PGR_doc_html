"""Настройки graph-service.

Все настройки читаются из переменных окружения контейнера.
Если переменная не задана - используется значение по умолчанию.
"""

from functools import lru_cache

from pydantic import AnyHttpUrl, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseSettings):
    redis_host: str = "redis"
    redis_port: int = 6379
    cache_db: int = 0


class Settings(BaseSettings):
    """Настройки приложения graph-service.

    Режим работы определяется по переменной VEHICLE_ID:
    - Если VEHICLE_ID = "+" или не задан - серверный режим
    - Если VEHICLE_ID задан (например "4") - бортовой режим
    """

    redis: RedisSettings = RedisSettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # === Режим работы ===
    vehicle_id: str = Field(
        default="+",
        description=(
            "ID транспортного средства: '+' для сервера (broadcast), конкретный ID для борта"
        ),
    )

    # === База данных ===
    postgres_host: str = Field(default="postgres", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_user: str = Field(default="postgres", description="PostgreSQL user")
    postgres_password: str = Field(default="postgres", description="PostgreSQL password")
    postgres_db: str = Field(default="dispatching_graph", description="PostgreSQL database name")

    # === MQTT ===
    nanomq_host: str = Field(default="nanomq", description="NanoMQ host")
    nanomq_mqtt_port: int = Field(default=1883, description="NanoMQ MQTT port")

    # === Серверный graph-service (для бортового режима) ===
    graph_service_server_host: str = Field(
        default="10.100.109.14",
        description="IP серверного graph-service для синхронизации",
    )
    graph_service_server_port: int = Field(
        default=8005,
        description="Порт серверного graph-service для синхронизации",
    )

    # === Trip Service ===
    trip_service_host: str = Field(
        default="dispatching-server-trip-service",
        description="Trip service host",
    )
    trip_service_port: int = Field(default=8000, description="Trip service port")

    # === Enterprise Service ===
    enterprise_service_host: str = Field(
        default="dispatching-server-enterprise-service",
        description="Enterprise service server host",
    )
    enterprise_service_internal_port: int = Field(
        default=8001,
        description="Enterprise service host port",
    )

    # === Analytics Service ===
    analytics_service_host: str = Field(
        default="analytics-service",
        description="Analytics service host",
    )
    analytics_service_port: int = Field(
        default=8000,
        description="Analytics service host port",
    )

    # === GPS → Canvas трансформация ===
    origin_gps_lat: float = Field(default=58.173161, description="GPS широта точки отсчета")
    origin_gps_lon: float = Field(default=59.818738, description="GPS долгота точки отсчета")
    origin_canvas_x: float = Field(default=0.0, description="Canvas X координата точки отсчета")
    origin_canvas_y: float = Field(default=0.0, description="Canvas Y координата точки отсчета")
    origin_canvas_z: float = Field(default=0.0, description="Canvas Z координата точки отсчета")

    # === Транспорт ===
    default_vehicle_height: float = Field(default=0.0, description="default vehicle height")

    # === Debug ===
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # === S3 хранилище ===
    s3_access_key: str = Field(..., description="s3 login")
    s3_secret_key: str = Field(..., description="s3 password")
    s3_endpoint_url: str = Field(default="http://10.100.109.14:9000", description="s3 endpoint")
    s3_region_name: str = Field(default="us-east-1", description="s3 region")
    s3_bucket_name: str = Field(default="graph-service", description="s3 bucket name")

    # === Playback кеш ===
    playback_cache_ttl: int = Field(
        default=3600,
        description="Playback cache TTL in Redis (seconds)",
    )
    playback_chunk_target_records: int = Field(default=1000, description="Target records per chunk")
    playback_chunk_min_duration: int = Field(
        default=10,
        description="Min chunk duration in seconds",
    )
    playback_chunk_max_duration: int = Field(
        default=300,
        description="Max chunk duration in seconds",
    )

    # === Вычисления маршрута ===
    deviation_threshold_m: int = Field(
        default=25,
        description="Допустимое отклонение от маршрута в метрах",
    )
    route_cache_ttl: int = Field(
        default=3600,
        description="Время хранения расчета маршрута в секундах",
    )

    @property
    def database_url(self) -> str:
        return PostgresDsn.build(
            scheme="postgresql",
            host=self.postgres_host,
            port=self.postgres_port,
            username=self.postgres_user,
            password=self.postgres_password,
            path=self.postgres_db,
        ).unicode_string()

    @property
    def is_server_mode(self) -> bool:
        """Серверный режим: vehicle_id = '+' или не задан."""
        return self.vehicle_id == "+" or not self.vehicle_id

    @property
    def is_bort_mode(self) -> bool:
        """Бортовой режим: vehicle_id - конкретный ID машины."""
        return self.vehicle_id != "+" and bool(self.vehicle_id)

    @property
    def mqtt_topic_vehicle_id(self) -> str:
        """ID для MQTT топика."""
        return self.vehicle_id

    @property
    def graph_service_server_url(self) -> str:
        """URL серверного graph-service."""
        return f"http://{self.graph_service_server_host}:{self.graph_service_server_port}"

    @property
    def trip_service_url(self) -> str:
        """URL trip-service."""
        return f"http://{self.trip_service_host}:{self.trip_service_port}"

    @property
    def enterprise_service_url(self) -> str:
        """URL enterprise-service."""
        return f"http://{self.enterprise_service_host}:{self.enterprise_service_internal_port}"

    @property
    def analytics_service_url(self) -> AnyHttpUrl:
        """URL analytics-service."""
        return AnyHttpUrl(f"http://{self.analytics_service_host}:{self.analytics_service_port}")


# Глобальный экземпляр настроек
@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
