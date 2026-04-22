"""Analytics service client for platform_sdk."""

from __future__ import annotations

from enum import StrEnum
from typing import TypeVar

from pydantic import BaseModel

from platform_sdk._base_client import AsyncBaseClient
from platform_sdk.analytics._models import (
    CycleTagHistoryField,
    CycleTagHistoryFilter,
    CycleTagHistoryResponse,
    PaginationResponse,
    SortDirection,
    VehicleTelemetryField,
    VehicleTelemetryFilter,
    VehicleTelemetryResponse,
)

__all__ = ["AsyncAnalyticsClient"]

T = TypeVar("T", bound=BaseModel)

_VEHICLE_TELEMETRY_PATH = "/api/v1/vehicle-telemetry"
_CYCLE_TAG_HISTORY_PATH = "/api/v1/trip_service/cycle-tag-history"


class AsyncAnalyticsClient:
    """Async client for the analytics service.

    Provides typed business methods for accessing vehicle telemetry and
    cycle tag history data. Composes AsyncBaseClient — does not inherit.
    """

    def __init__(self, client: AsyncBaseClient) -> None:
        self._client = client

    async def get_vehicle_telemetry(
        self,
        root: VehicleTelemetryFilter,
        *,
        skip: int = 0,
        limit: int = 100,
        sort_by: VehicleTelemetryField | None = None,
        sort_direction: SortDirection = SortDirection.ASC,
    ) -> PaginationResponse[VehicleTelemetryResponse]:
        """Retrieve vehicle telemetry records matching the filter.

        Args:
            root: Root of the filter tree — either a single FilterParam
                or a FilterGroup. Sent as JSON in the POST request body.
            skip: Number of records to skip (offset-based pagination).
            limit: Maximum number of records to return.
            sort_by: Field to sort by. If None, server default ordering applies.
            sort_direction: Sort direction. Only used when sort_by is set.

        Returns:
            PaginationResponse with page metadata and the list of telemetry rows.
        """
        return await self._list(
            _VEHICLE_TELEMETRY_PATH,
            root=root,
            response_item=VehicleTelemetryResponse,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )

    async def get_cycle_tag_history(
        self,
        root: CycleTagHistoryFilter,
        *,
        skip: int = 0,
        limit: int = 100,
        sort_by: CycleTagHistoryField | None = None,
        sort_direction: SortDirection = SortDirection.ASC,
    ) -> PaginationResponse[CycleTagHistoryResponse]:
        """Retrieve cycle tag history records from the trip service.

        Same shape as get_vehicle_telemetry — see its docstring.
        """
        return await self._list(
            _CYCLE_TAG_HISTORY_PATH,
            root=root,
            response_item=CycleTagHistoryResponse,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )

    async def _list(
        self,
        path: str,
        *,
        root: BaseModel,
        response_item: type[T],
        skip: int,
        limit: int,
        sort_by: StrEnum | None,
        sort_direction: SortDirection,
    ) -> PaginationResponse[T]:
        """Shared POST-list helper for paginated, filterable resources."""
        params: dict[str, str | int] = {"skip": skip, "limit": limit}
        if sort_by is not None:
            params["sort_by"] = sort_by.value
            params["sort_type"] = sort_direction.value

        return await self._client.request_model(
            "POST",
            path,
            PaginationResponse[response_item],  # type: ignore[valid-type]
            json={"chain": root.model_dump(mode="json")},
            params=params,
        )
