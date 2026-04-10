from enum import StrEnum
from typing import NewType

NanoID = NewType("NanoID", str)


class CompressionAlgorithm(StrEnum):
    """Available compression algorithms."""

    NONE = "none"
    GZIP = "gzip"
    LZ4B = "lz4b"


class AutorepubConfigType(StrEnum):
    """Autorepub config types."""

    MQTT = "mqtt"
    RABBITMQ = "rabbitmq"
