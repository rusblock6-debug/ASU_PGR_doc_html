"""Роутер для работы с видами грузов."""

from typing import Annotated

from auth_lib import Action, Permission, require_permission
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from starlette import status

from app.database.engine import Session
from app.schemas.load_type import (
    APICreateLoadType,
    APILoadTypeResponseModel,
    APILoadTypesResponseModel,
    APIUpdateLoadType,
)
from app.services.crud.load_type import LoadTypeCRUD

router = APIRouter(prefix="/load_types", tags=["Load Types"])


def get_crud_service(session: Session) -> LoadTypeCRUD:
    """Получить экземпляр сервиса LoadTypeCRUD."""
    return LoadTypeCRUD(session)


ServiceCRUD = Annotated[LoadTypeCRUD, Depends(get_crud_service)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=APILoadTypeResponseModel,
    dependencies=[Depends(require_permission((Permission.CARGO, Action.EDIT)))],
)
async def create_load_type(
    data: APICreateLoadType,
    crud_service: ServiceCRUD,
) -> APILoadTypeResponseModel:
    """Создать вид груза."""
    try:
        created_load_type = await crud_service.create_obj(obj_in=data)
        return created_load_type  # type: ignore[return-value]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/{id}",
    response_model=APILoadTypeResponseModel | None,
    dependencies=[Depends(require_permission((Permission.CARGO, Action.VIEW)))],
)
async def get_load_type(id: int, crud_service: ServiceCRUD) -> APILoadTypeResponseModel | None:
    """Получение вида груза по ID."""
    try:
        load_type = await crud_service.get_by_id(id)
        return load_type  # type: ignore[return-value]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "",
    response_model=APILoadTypesResponseModel,
    dependencies=[
        Depends(
            require_permission(
                (Permission.WORK_ORDER, Action.VIEW),
                (Permission.CARGO, Action.VIEW),
                (Permission.PLACES, Action.VIEW),
            ),
        ),
    ],
)
async def get_load_types(
    crud_service: ServiceCRUD,
    page: int | None = Query(
        None,
        ge=1,
        description="Номер страницы (опционально, если не указан - возвращает все записи)",
    ),
    size: int | None = Query(
        None,
        ge=1,
        le=100,
        description="Размер страницы (опционально, если не указан - возвращает все записи)",
    ),
) -> APILoadTypesResponseModel:
    """Получение списка видов грузов с пагинацией или без неё.

    Если параметры page и size не указаны, возвращает все записи без пагинации.
    """
    try:
        result = await crud_service.get_all(page=page, size=size)
        items = [
            APILoadTypeResponseModel.model_validate(load_type) for load_type in result["items"]
        ]
        return APILoadTypesResponseModel(
            page=result["page"],
            pages=(result["total"] + result["size"] - 1) // result["size"]
            if result["size"] > 0
            else 1,
            size=len(items),
            total=result["total"],
            items=items,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.put(
    "/{id}",
    response_model=APILoadTypeResponseModel,
    dependencies=[Depends(require_permission((Permission.CARGO, Action.EDIT)))],
)
async def update_load_type(
    crud_service: ServiceCRUD,
    id: int,
    update_data: APIUpdateLoadType,
) -> APILoadTypeResponseModel:
    """Обновить все поля в модели вида грузов."""
    try:
        load_type = await crud_service.get(id)
        if load_type is None:
            raise ValueError(f"Вид груза с ID {id} не найден")
        return await crud_service.update_obj(session_obj=load_type, obj_in=update_data)  # type: ignore[return-value]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.delete(
    "/{id}",
    dependencies=[
        Depends(
            require_permission(
                (Permission.CARGO, Action.EDIT),
            ),
        ),
    ],
)
async def delete_load_type(id: int, crud_service: ServiceCRUD) -> Response:
    """Удалить запись по ID из таблицы вида грузов."""
    try:
        await crud_service.delete_obj(id=id)
        return Response(status_code=status.HTTP_200_OK)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
