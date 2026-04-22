# Platform SDK

Typed async Python SDK for internal UGMK platform HTTP services.

## Installation

```bash
uv add platform-sdk
```

Or with pip:

```bash
pip install platform-sdk
```

## Quick Start

```python
import asyncio
from platform_sdk import (
    AsyncClients,
    ClientSettings,
    FilterGroup,
    FilterParam,
    FilterType,
    QueryOperator,
    SortDirection,
    VehicleTelemetryField,
)


settings = ClientSettings(base_url="http://analytics-service")


async def main():
    async with AsyncClients(settings) as clients:
        result = await clients.analytics.get_vehicle_telemetry(
            root=FilterGroup[VehicleTelemetryField](
                type=FilterType.AND,
                items=[
                    FilterParam[VehicleTelemetryField](
                        field=VehicleTelemetryField.BORT,
                        value="A123",
                        operator=QueryOperator.EQUALS,
                    ),
                ],
            ),
            skip=0,
            limit=50,
            sort_by=VehicleTelemetryField.TIMESTAMP,
            sort_direction=SortDirection.DESC,
        )

        for row in result.data:
            print(f"{row.bort} | {row.timestamp} | {row.lat}, {row.lon} | speed={row.speed}")

        print(f"Total: {result.total_count}, page {result.page}/{result.total_pages}")


asyncio.run(main())
```

A single condition is also a valid filter — you do not have to wrap it:

```python
result = await clients.analytics.get_vehicle_telemetry(
    root=FilterParam[VehicleTelemetryField](
        field=VehicleTelemetryField.BORT,
        value="A123",
        operator=QueryOperator.EQUALS,
    ),
)
```

## Configuration

```python
from platform_sdk import ClientSettings, RetryEvent

def on_retry(event: RetryEvent) -> None:
    # Push to your metrics, logger or tracer.
    print(f"retry #{event.attempt} for {event.method} {event.url}: {event.exception!r}")

settings = ClientSettings(
    base_url="http://analytics-service",
    timeout={"connect": 5.0, "read": 30.0, "write": 10.0, "pool": 5.0},
    retry={"max_attempts": 3, "max_wait": 60.0},
    headers={"X-Custom-Header": "value"},
    verify_ssl=True,
    on_retry=on_retry,
)
```

All settings are validated via pydantic v2 and immutable after construction.

## Filter Tree

Filters are generic over the field enum of the resource. The same shapes
serve every resource — only the type parameter changes.

```python
from platform_sdk import (
    FilterGroup, FilterParam, FilterType, QueryOperator, VehicleTelemetryField,
)

# Simple: one condition (no wrapping needed when passing to the client).
single = FilterParam[VehicleTelemetryField](
    field=VehicleTelemetryField.BORT, value="A123", operator=QueryOperator.EQUALS,
)

# Complex: nested AND/OR
nested = FilterGroup[VehicleTelemetryField](
    type=FilterType.AND,
    items=[
        FilterParam[VehicleTelemetryField](
            field=VehicleTelemetryField.SPEED, value=60.0, operator=QueryOperator.GREATER,
        ),
        FilterGroup[VehicleTelemetryField](
            type=FilterType.OR,
            items=[
                FilterParam[VehicleTelemetryField](
                    field=VehicleTelemetryField.BORT, value=["A123", "B456"], operator=QueryOperator.IN,
                ),
            ],
        ),
    ],
)
```

`FilterParam` validates the value/operator pair: `IN` and `NOT_IN` require a
list, every other operator requires a scalar (or `None`).

### Available Fields

- Vehicle telemetry: `BORT`, `TIMESTAMP`, `LAT`, `LON`, `HEIGHT`, `SPEED`, `FUEL`
- Cycle tag history: `ID`, `TIMESTAMP`, `VEHICLE_ID`, `CYCLE_ID`, `PLACE_ID`, `PLACE_NAME`, `PLACE_TYPE`, `TAG_ID`, `TAG_NAME`, `TAG_EVENT`

### Available Operators

`EQUALS`, `NOT_EQUAL`, `IN`, `NOT_IN`, `GREATER`, `EQUALS_OR_GREATER`, `LESS`, `EQUALS_OR_LESS`, `STARTS_WITH`, `NOT_START_WITH`, `ENDS_WITH`, `NOT_END_WITH`, `CONTAINS`, `NOT_CONTAIN`

## Error Handling

All HTTP and network errors are wrapped in SDK-specific exceptions:

```python
from platform_sdk import (
    AsyncClients, ClientSettings,
    NotFoundError, ServerError, SDKTimeoutError, ResponseParseError,
)

settings = ClientSettings(base_url="http://analytics-service")

async with AsyncClients(settings) as clients:
    try:
        result = await clients.analytics.get_vehicle_telemetry(root=root)
    except NotFoundError:
        print("Endpoint not found")
    except ServerError as e:
        print(f"Server error {e.status_code}: {e.response_body}")
    except SDKTimeoutError:
        print("Request timed out")
    except ResponseParseError as e:
        print(f"Server returned {e.status_code} but body could not be decoded:\n{e.response_body}")
```

### Exception Hierarchy

```
SDKError
  TransportError
    ConnectError
    SDKTimeoutError
  ResponseError
    BadRequestError              (400)
    UnauthorizedError            (401)
    ForbiddenError               (403)
    NotFoundError                (404)
    ConflictError                (409)
    UnprocessableEntityError     (422 — server rejected our payload)
    RateLimitError               (429)
    ServerError                  (5xx)
  ResponseParseError             (response received, body could not be decoded)
```

`SDKTimeoutError` does not shadow the built-in `TimeoutError`. `ResponseParseError`
sits next to `ResponseError` deliberately: a 422 from the server and a JSON
the SDK cannot decode are different problems.

## Transport Features

- **Connection pooling** via httpx (100 max connections, 20 keep-alive)
- **Automatic retry** with exponential backoff + jitter on 429, 500, 502, 503, 504 and network errors
- **No retry** on 4xx business errors (400, 401, 403, 404, 409, 422)
- **`X-Request-ID`** auto-generated and sent on every outgoing request; the same id appears in logs and in the `RetryEvent` callback for end-to-end correlation
- **Retry observability** — each retry emits a WARNING log; provide `on_retry` in `ClientSettings` for metrics or custom handling
- **Structured logging** with sensitive header masking (Authorization, API keys)

## Migrating from 0.1 to 0.2

| 0.1                                          | 0.2                                              |
|----------------------------------------------|--------------------------------------------------|
| `TimeoutError`                               | `SDKTimeoutError`                                |
| `ValidationError` (HTTP 422)                 | `UnprocessableEntityError`                       |
| `ValidationError` (response decode failure)  | `ResponseParseError`                             |
| `SortTypeEnum`                               | `SortDirection`                                  |
| `sort_type=`                                 | `sort_direction=`                                |
| `chain=`                                     | `root=`                                          |
| `CycleTagHistoryFilterParam` / `Group`       | `FilterParam[CycleTagHistoryField]` / `FilterGroup[CycleTagHistoryField]` |
| `client._post(...)` (private)                | `client.request_model("POST", ...)` (public)     |

`AsyncClients` now raises `RuntimeError` if accessed outside an `async with`
block instead of failing later with `AttributeError`. `FilterParam` rejects
`IN`/`NOT_IN` with a scalar value (and vice versa) at construction time.

## Requirements

- Python 3.11+
- httpx
- pydantic v2
- tenacity

## Development

```bash
# Install with dev dependencies
uv sync

# Run tests
uv run pytest tests/ -v

# Type checking
uv run mypy platform_sdk/ --strict

# Linting
uv run ruff check platform_sdk/

# Build
uv build
```

## License

Internal use only.
