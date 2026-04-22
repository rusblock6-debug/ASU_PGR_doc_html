import json
import logging
from functools import cached_property

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.models.types import CompressionAlgorithm


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=None,  # Don't load from .env file by default
        case_sensitive=False,  # Case-insensitive environment variable names
    )

    instance_id: str = Field(default="instance-not-found-in-env")

    # MQTT settings
    mqtt_broker_host: str = Field(default="not_found_in_env")
    mqtt_broker_port: int = Field(default=1883)

    # Autorepub MQTT settings
    autorepub_mqtt_broker_host: str = Field(default="not_found_in_env")
    autorepub_mqtt_broker_port: int = Field(default=1883)

    # RabbitMQ settings
    rabbitmq_dsn: str = Field(default="amqp://not_found_in_env:not_found_in_env@not_found_in_env:5672/")

    # Database settings
    redis_url: str = Field(default="redis://not_found_in_env:6379/0")

    # Message Protocol settings
    id_length: int = Field(
        default=10, ge=1, le=255,
        description="Length of message ID (bytes). Alphabet supposed to contain only 1 byte UTF-8 chars"
    )
    chunk_size: int = Field(default=58, description="Maximal chunk size (bytes)", gt=0)
    max_size: int = Field(
        default=1048576, gt=0, description="Maximum message size before fragmentation (bytes, 1048576 B == 1 MB)"
    )

    # Compression settings
    compression_algo: CompressionAlgorithm = Field(
        default=CompressionAlgorithm.LZ4B,
        description="Compression algorithm for message payloads"
    )
    compression_min_size: int = Field(
        default=44, ge=0, description="Minimum message size for compression (bytes)"
    )

    # Retry settings
    retry_max_attempts: int = Field(default=100, ge=-1, description="Max retry attempts (-1 - infinite, 0 - exactly 0)")
    retry_backoff_base: int = Field(default=2000, ge=0, description="Base retry backoff (milliseconds)")
    retry_multiplier: int = Field(default=2, ge=1, description="Retry multiplier for exponential backoff")
    retry_max_delay: int = Field(default=60000, ge=0, description="Maximum retry delay (milliseconds)")

    # Message Storage settings
    common_redis_ttl: int = Field(default=3600, gt=0, description="Common TTL for Redis keys (seconds)")
    # Deduplication settings
    dedup_redis_ttl: int = Field(default=13 * 3600, gt=0, description="TTL for dedup Redis keys (seconds)")

    # Cleanup settings
    cleanup_interval_seconds: int = Field(
        default=300, ge=0, description="How often to run cleanup of inmemory data (seconds)"
    )
    max_message_age_hours: int = Field(default=6, ge=0, description="Max age before abandoning message (hours)")
    incomplete_receive_timeout_minutes: int = Field(
        default=30, ge=0, description="Timeout for incomplete receives (minutes)"
    )

    # Runtime settings
    log_level: str = Field(default="INFO", description="Logging level")
    debug_mode: bool = Field(
        default=False,
        description="If enabled, target RabbitMQ queues and MQTT topics will be prefixed with 'test'",
    )
    mode: str = Field(default="dev", description="'dev' for local development with autoreload, otherwise 'prod'")
    multi_replica_mode: bool = Field(
        default=False,
        description=(
            "Activate to enable coordination mechanics to distribute workload between "
            "several neigbour replicas with same instance_id"
        ),
    )
    hostname: str = Field(
        default="not_found_in_env", description="Containers hostname used as replica_id for multi replica mode"
    )
    remote_instances: str = Field(
        default="", description="Remote instance IDs (separated by commas)"
    )

    @cached_property
    def header_size(self) -> int:
        """
        Calculate header size based on nanoid length.
            n (nanoid) + 2 (index) + 2 (total) + 1 (flags) = 5 + n bytes
        """
        return self.id_length + 5

    @cached_property
    def payload_size(self) -> int:
        """Calculate payload size by subtracting header size from chunk size."""
        return self.chunk_size - self.header_size

    @classmethod
    def _split_by_commas(cls, value: str) -> list[str]:
        return [name.strip() for name in value.split(",") if name.strip()]

    @cached_property
    def remote_instances_list(self) -> list[str]:
        """Get parsed list of Remote instance IDs."""
        return self._split_by_commas(self.remote_instances)

    @field_validator("log_level", mode="before")
    @classmethod
    def parse_log_level(cls, v: str) -> str:
        """Parse log_level from string."""
        v_upper = v.upper()
        if v_upper not in logging._nameToLevel:
            raise ValueError(f"Invalid log level: {v}")
        return v_upper

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        """Validate settings after all fields are set."""

        # Validate chunk_size is large enough for header
        if self.chunk_size <= self.header_size:
            raise ValueError(
                f"CHUNK_SIZE {self.chunk_size} must be greater than header size {self.header_size} "
                f"(id_length={self.id_length})"
            )

        # Validate that max message size doesn't exceed uint16 chunk limit (65535 chunks)
        max_chunks_needed = (self.max_size + self.payload_size - 1) // self.payload_size
        if max_chunks_needed > 65535:
            max_allowed_size = 65535 * self.payload_size
            raise ValueError(
                f"MAX_MESSAGE_SIZE {self.max_size} would require {max_chunks_needed} chunks, "
                f"exceeding uint16 limit (65535). Maximum allowed size is {max_allowed_size} bytes "
                f"with payload size {self.payload_size}."
            )

        return self

    def log_dump(self, *, _logger: logging.Logger) -> None:
        """Log all settings."""
        payload = json.dumps(self.model_dump(), indent=2, default=str)
        _logger.info("Loaded settings:\n%s", payload)


# Global settings instance
settings = Settings()
