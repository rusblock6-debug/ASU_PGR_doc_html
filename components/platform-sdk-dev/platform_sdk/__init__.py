"""platform_sdk — typed Python SDK for UGMK platform services.

Public API surface:
- AsyncClients: top-level facade, use as `async with AsyncClients(settings) as clients:`
- ClientSettings, RetryEvent: SDK configuration
- SDKError and subclasses: exception hierarchy
- AsyncAnalyticsClient: analytics service client
- Filter/response models: FilterGroup, FilterParam, PaginationResponse, etc.
"""

from platform_sdk._clients import AsyncClients
from platform_sdk._exceptions import (
    BadRequestError,
    ConflictError,
    ConnectError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ResponseError,
    ResponseParseError,
    SDKError,
    SDKTimeoutError,
    ServerError,
    TransportError,
    UnauthorizedError,
    UnprocessableEntityError,
)
from platform_sdk._settings import (
    ClientSettings,
    OnRetry,
    RetryEvent,
    RetrySettings,
    TimeoutSettings,
)
from platform_sdk.analytics import (
    AsyncAnalyticsClient,
    CycleTagHistoryField,
    CycleTagHistoryFilter,
    CycleTagHistoryResponse,
    FilterGroup,
    FilterParam,
    FilterType,
    FilterValue,
    PaginationResponse,
    QueryOperator,
    SortDirection,
    VehicleTelemetryField,
    VehicleTelemetryFilter,
    VehicleTelemetryResponse,
)

__all__ = [
    # Top-level
    "AsyncClients",
    # Settings
    "ClientSettings",
    "OnRetry",
    "RetryEvent",
    "RetrySettings",
    "TimeoutSettings",
    # Exceptions — base
    "SDKError",
    # Exceptions — transport
    "TransportError",
    "ConnectError",
    "SDKTimeoutError",
    # Exceptions — response
    "ResponseError",
    "BadRequestError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ConflictError",
    "UnprocessableEntityError",
    "RateLimitError",
    "ServerError",
    "ResponseParseError",
    # Analytics
    "AsyncAnalyticsClient",
    "CycleTagHistoryField",
    "CycleTagHistoryFilter",
    "CycleTagHistoryResponse",
    "FilterGroup",
    "FilterParam",
    "FilterType",
    "FilterValue",
    "PaginationResponse",
    "QueryOperator",
    "SortDirection",
    "VehicleTelemetryField",
    "VehicleTelemetryFilter",
    "VehicleTelemetryResponse",
]
