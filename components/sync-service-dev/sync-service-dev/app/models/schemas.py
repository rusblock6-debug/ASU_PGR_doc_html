from functools import cached_property

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.types import AutorepubConfigType
from app.settings import settings


class AutorepubConfig(BaseModel):
    """Autorepub configuration."""
    # TODO: split to AutorepubConfigMQTT (source_topic, target_topic) and AutorepubConfigRabbitMQ (queue_name)

    name: str = Field(description="Unique name identifier for this config")
    type: AutorepubConfigType = Field(description="Autorepub config type (MQTT or RabbitMQ)")

    source_instance_id: str = Field(
        default=settings.instance_id,
        description="Config is only loaded on this instance. If None, will be settings.instance_id"
    )
    target_instances: str = Field(
        default=settings.remote_instances,
        description=(
            "Receiver instance IDs (can be multiple IDs separated by commas). "
            "If None, will be settings.remote_instances"
        )
    )

    source_topic: str = Field(default="", description="MQTT topic to subscribe to")
    target_topic: str | None = Field(
        default=None, description="MQTT topic to republish to (None = use source_topic)"
    )

    queue_name: str = Field(
        default="common",
        description="Queue name for AutorepubConfigType.RabbitMQ messages (default: 'common')",
    )

    deduplication: bool = Field(
        default=False,
        description="If True, messages will be deduplicated on the receiver side by msg_id",
    )
    autostart: bool = Field(
        default=False, description="If True, automatically activate config on startup if Redis key doesn't exist"
    )

    retry_max_attempts: int = Field(
        default=settings.retry_max_attempts, description="Max retry attempts (default is use global config)"
    )
    retry_backoff_base: int = Field(
        default=settings.retry_backoff_base, description="Retry backoff base in ms (default is use global config)"
    )
    retry_multiplier: int = Field(
        default=settings.retry_multiplier, description="Retry multiplier (default is use global config)"
    )
    retry_max_delay: int = Field(
        default=settings.retry_max_delay, description="Retry max delay in ms (default is use global config)"
    )

    @property
    def is_debug(self) -> bool:
        return self.name.startswith("_")

    def get_target_topic(self) -> str:
        """Get target topic, defaulting to source_topic if not specified."""
        return self.target_topic if self.target_topic else self.source_topic

    @field_validator("source_instance_id", mode="before")
    @classmethod
    def parse_source_instance_id(cls, v: str | None) -> str:
        """Parse source_instance_id."""
        if v is None:
            return settings.instance_id
        return v

    @field_validator("target_instances", mode="before")
    @classmethod
    def parse_target_instances(cls, v: str | None) -> str:
        """Parse target_instances."""
        if v is None:
            return settings.remote_instances
        return v

    @cached_property
    def target_instances_list(self) -> list[str]:
        """Get parsed list of Receiver instance IDs."""
        if self.target_instances is None:
            return []
        return self._split_by_commas(self.target_instances)

    @classmethod
    def _split_by_commas(cls, value: str) -> list[str]:
        return [name.strip() for name in value.split(",") if name.strip()]

    @model_validator(mode="after")
    def validate_mqtt_config(self) -> "AutorepubConfig":
        """Validate aspects specific for MQTT config."""

        if self.type == AutorepubConfigType.MQTT:
            if not self.source_topic:
                raise ValueError("source_topic must be populated for MQTT configs")
            if self.retry_max_attempts != 0:
                raise ValueError("Retries are currently incompatible with MQTT configs")

        return self


class DeliveryParams(BaseModel):
    """Delivery parameters."""

    receiver_id: str = Field(description="Receiver instance ID")
    type: AutorepubConfigType = Field(description="Transfer type (MQTT or RabbitMQ)")

    deduplication: bool = Field(
        default=False,
        description="If True, messages will be deduplicated on the receiver side by msg_id",
    )
    retry_max_attempts: int = Field(default=settings.retry_max_attempts, description="Max retry attempts")
    retry_backoff_base: int = Field(default=settings.retry_backoff_base, description="Retry backoff base in ms")
    retry_multiplier: int = Field(default=settings.retry_multiplier, description="Retry multiplier")
    retry_max_delay: int = Field(default=settings.retry_max_delay, description="Retry max delay in ms")
