# ruff: noqa: D100, D103
"""Vehicle Telemetry маршруты."""

from fastapi import APIRouter, Depends

from src.app.controller import VehicleTelemetryController
from src.app.fastapi_factory import FastAPIFactory
from src.app.scheme.vehicle_telemetry import (
    VehicleTelemetryFilterRequest,
    VehicleTelemetryResponse,
)
from src.core.dto.scheme.response.pagination import PaginationResponse
from src.core.dto.type.sort import SortTypeEnum

router = APIRouter(
    prefix="/vehicle-telemetry",
    tags=["Vehicle Telemetry"],
)


@router.post(
    "",
    response_model=PaginationResponse[VehicleTelemetryResponse],
    summary="Vehicle telemetry with filters",
)
async def get_by_filters(
    body: VehicleTelemetryFilterRequest,
    skip: int = 0,
    limit: int = 100,
    sort_by: str | None = None,
    sort_type: SortTypeEnum | None = SortTypeEnum.asc,
    controller: VehicleTelemetryController = Depends(
        FastAPIFactory.get_vehicle_telemetry_controller,
    ),
) -> PaginationResponse:  # type: ignore[type-arg]
    return await controller.get_by_filters(
        filter_request=body,  # type: ignore[arg-type]
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_type=sort_type.value if sort_type else "asc",
    )
