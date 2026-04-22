# ruff: noqa: D100, D103
"""Cycle Tag History маршруты."""

from fastapi import APIRouter, Depends

from src.app.controller.cycle_tag_history import CycleTagHistoryController
from src.app.fastapi_factory import FastAPIFactory
from src.app.scheme.cycle_tag_history import (
    CycleTagHistoryFilterRequest,
    CycleTagHistoryResponse,
)
from src.core.dto.scheme.response.pagination import PaginationResponse
from src.core.dto.type.sort import SortTypeEnum

router = APIRouter(
    prefix="/cycle-tag-history",
)


@router.post(
    "",
    response_model=PaginationResponse[CycleTagHistoryResponse],
    summary="Cycle tag history with filters",
)
async def get_by_filters(
    body: CycleTagHistoryFilterRequest,
    skip: int = 0,
    limit: int = 100,
    sort_by: str | None = None,
    sort_type: SortTypeEnum | None = SortTypeEnum.asc,
    controller: CycleTagHistoryController = Depends(
        FastAPIFactory.get_cycle_tag_history_controller,
    ),
) -> PaginationResponse:  # type: ignore[type-arg]
    return await controller.get_by_filters(
        filter_request=body,  # type: ignore[arg-type]
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_type=sort_type.value if sort_type else "asc",
    )
