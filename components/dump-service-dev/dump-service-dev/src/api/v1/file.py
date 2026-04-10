"""Маршруты API для работы с файлами dump-service."""

from fastapi import APIRouter, Depends

from src.api.dependency.request import get_pagination_params, get_sort_params
from src.app import model
from src.app.controller import FileController
from src.app.factory import Factory
from src.app.scheme import response
from src.core.dto.scheme.response.pagination import PaginationResponse
from src.core.dto.type.pagination import PaginationParams
from src.core.dto.type.sort import SortParams

router = APIRouter(
    prefix="/file",
    tags=["File"],
)


@router.get("", response_model=PaginationResponse[response.File])
async def get_all(
    pagination_params: PaginationParams = Depends(get_pagination_params),
    sort_params: SortParams = Depends(get_sort_params),
    file_controller: FileController = Depends(Factory().get_file_controller),
) -> PaginationResponse[model.File]:
    """Получить все файлы в дамп сервисе."""
    return await file_controller.get_all(
        sort_by=sort_params.sort_by,
        sort_type=sort_params.sort_type,
        skip=pagination_params.skip,
        limit=pagination_params.limit,
    )
