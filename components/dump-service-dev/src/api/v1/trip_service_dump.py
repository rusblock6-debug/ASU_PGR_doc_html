"""API trip-service dump."""

from fastapi import APIRouter, Depends

from src.api.dependency.request import get_pagination_params, get_sort_params
from src.app import model
from src.app.controller import TripController
from src.app.factory import Factory
from src.app.scheme import response
from src.core.dto.scheme.response.pagination import PaginationResponse
from src.core.dto.type.pagination import PaginationParams
from src.core.dto.type.sort import SortParams

router = APIRouter(
    prefix="/trip-service",
    tags=["TripService Dump"],
)


@router.post("/dump", response_model=response.TripServiceDump)
async def create_dump(
    trip_id: str,
    trip_controller: TripController = Depends(Factory().get_trip_controller),
) -> model.TripServiceDump:
    """Триггер для дампа trip service."""
    result = await trip_controller.generate_dump(trip_id)
    return result


@router.get("/dump", response_model=PaginationResponse[response.TripServiceDump])
async def get_dump_all(
    pagination: PaginationParams = Depends(get_pagination_params),
    sort: SortParams = Depends(get_sort_params),
    trip_controller: TripController = Depends(Factory().get_trip_controller),
) -> PaginationResponse[response.TripServiceDump]:
    """Получить список дампов для trip-service."""
    return await trip_controller.get_all(
        sort_type=sort.sort_type,
        sort_by=sort.sort_by,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get("/dump/{dump_id}", response_model=response.TripServiceDump)
async def get_dump(
    dump_id: int,
    trip_controller: TripController = Depends(Factory().get_trip_controller),
) -> model.TripServiceDump:
    """Получить dump по id для trip-service."""
    return await trip_controller.get_by_id(dump_id)
