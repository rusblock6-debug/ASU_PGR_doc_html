from pydantic import AmqpDsn, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseServiceSettings(BaseSettings):
    """Base class for database service settings."""

    POSTGRES_HOST: str | None = None
    POSTGRES_PORT: int | None = None
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_DATABASE: str | None = None

    @property
    def POSTGRES_URL(self) -> str | None:
        if self.POSTGRES_HOST is None:
            return None
        return PostgresDsn.build(
            scheme="postgresql",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=f"{self.POSTGRES_DATABASE}",
        ).unicode_string()


class GraphServiceSettings(DatabaseServiceSettings):
    """Graph service database settings."""

    pass


class EnterpriseServiceSettings(DatabaseServiceSettings):
    """Enterprise service database settings."""

    pass


class AuthServiceSettings(DatabaseServiceSettings):
    """Auth service database settings."""

    pass


class TripServiceSettings(DatabaseServiceSettings):
    """Auth service database settings."""

    pass


class RetrySettings(BaseSettings):
    MAX_RETRIES: int = Field(default=5)
    INITIAL_DELAY: float = Field(default=1.0)
    MAX_DELAY: float = Field(default=60.0)
    EXPONENTIAL_BASE: float = Field(default=2.0)
    JITTER: bool = Field(default=True)


class Settings(BaseSettings):
    VEHICLE_ID: int = 4

    RABBIT_AMQP_HOST: str
    RABBIT_AMQP_PORT: int
    RABBIT_AMQP_USER: str
    RABBIT_AMQP_PASSWORD: str
    RABBIT_AMQP_VHOST: str = "/"

    @property
    def AMQP_URL(self) -> str:
        return AmqpDsn.build(
            scheme="amqp",
            username=self.RABBIT_AMQP_USER,
            password=self.RABBIT_AMQP_PASSWORD,
            host=self.RABBIT_AMQP_HOST,
            port=self.RABBIT_AMQP_PORT,
            path=self.RABBIT_AMQP_VHOST if self.RABBIT_AMQP_VHOST != "/" else "",
        ).unicode_string()

    PREFETCH_COUNT: int = 1

    # nested settings: читаются из env как GRAPH_SERVICE__POSTGRES_HOST и т.д.
    graph_service: GraphServiceSettings = GraphServiceSettings()
    enterprise_service: EnterpriseServiceSettings = EnterpriseServiceSettings()
    auth_service: AuthServiceSettings = AuthServiceSettings()
    trip_service: TripServiceSettings = TripServiceSettings()
    retry: RetrySettings = RetrySettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )


settings = Settings()  # type: ignore[call-arg]
