from enum import StrEnum


class PointTypeEnum(StrEnum):
    loading = "loading"
    unloading = "unloading"
    transfer = "transfer"
    transit = "transit"
    transport = "transport"
    node = "node"
