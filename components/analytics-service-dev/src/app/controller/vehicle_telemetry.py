# ruff: noqa: D100, D101, D102
from msgspec.structs import asdict

from src.app.repository import VehicleTelemetryRepository
from src.core.dto.scheme.response.pagination import PaginationResponse
from src.core.filter import FilterRequest


class VehicleTelemetryController:
    def __init__(
        self,
        vehicle_telemetry_repository: VehicleTelemetryRepository,
    ) -> None:
        self.vehicle_telemetry_repository = vehicle_telemetry_repository

    async def get_by_filters(
        self,
        filter_request: FilterRequest | None = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_type: str | None = "asc",
    ) -> PaginationResponse:  # type: ignore[type-arg]
        data = await self.vehicle_telemetry_repository.get_by_filters(
            filter_request=filter_request,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_type=sort_type,
        )
        total_count = await self.vehicle_telemetry_repository.count(
            filter_request=filter_request,
        )
        page = skip // limit + 1 if limit > 0 else 1
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

        return PaginationResponse(
            data=[asdict(item) for item in data],
            page=page,
            page_size=len(data),
            total_pages=total_pages,
            total_count=total_count,
        )
