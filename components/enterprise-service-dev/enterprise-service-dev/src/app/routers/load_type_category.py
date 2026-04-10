"""Роутер для работы с категориями видов грузов."""

from typing import Annotated

from auth_lib import Action, Permission, require_permission
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.exc import IntegrityError
from starlette import status

from app.database.engine import Session
from app.schemas.load_type_categories import (
    APICreateLoadTypeCategories,
    APIResponseLoadTypeCategoriesModel,
    APIResponseLoadTypeCategoryModel,
    APIUpdateLoadTypeCategories,
)
from app.services.crud.load_type_category import LoadTypeCategoryCRUD

router = APIRouter(prefix="/load_type_categories", tags=["Load Type Categories"])


def get_crud_service(session: Session) -> LoadTypeCategoryCRUD:
    """Получить экземпляр сервиса LoadTypeCategoryCRUD."""
    return LoadTypeCategoryCRUD(session)


ServiceCRUD = Annotated[LoadTypeCategoryCRUD, Depends(get_crud_service)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=APIResponseLoadTypeCategoryModel,
    dependencies=[Depends(require_permission((Permission.CARGO, Action.EDIT)))],
)
async def create_load_type_categories(
    data: APICreateLoadTypeCategories,
    crud_service: ServiceCRUD,
) -> APIResponseLoadTypeCategoryModel:
    """Создать категорию вида груза."""
    try:
        created_load_type = await crud_service.create_obj(obj_in=data)
        return created_load_type  # type: ignore[return-value]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/{id}",
    response_model=APIResponseLoadTypeCategoryModel | None,
    dependencies=[Depends(require_permission((Permission.CARGO, Action.VIEW)))],
)
async def get_load_type_category(
    id: int,
    crud_service: ServiceCRUD,
) -> APIResponseLoadTypeCategoryModel | None:
    """Получение категории вида груза по ID."""
    try:
        load_type = await crud_service.get(id)
        return load_type  # type: ignore[return-value]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "",
    response_model=APIResponseLoadTypeCategoriesModel,
    dependencies=[Depends(require_permission((Permission.CARGO, Action.VIEW)))],
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
) -> APIResponseLoadTypeCategoriesModel:
    """Получение списка категорий видов грузов с пагинацией или без неё.

    Если параметры page и size не указаны, возвращает все записи без пагинации.
    """
    try:
        result = await crud_service.get_all(page=page, size=size)
        items = [
            APIResponseLoadTypeCategoryModel.model_validate(category)
            for category in result["items"]
        ]
        return APIResponseLoadTypeCategoriesModel(
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
    response_model=APIResponseLoadTypeCategoryModel,
    dependencies=[Depends(require_permission((Permission.CARGO, Action.EDIT)))],
)
async def update_load_type(
    crud_service: ServiceCRUD,
    id: int,
    update_data: APIUpdateLoadTypeCategories,
) -> APIResponseLoadTypeCategoryModel:
    """Обновить все поля в модели категории вида грузов."""
    try:
        load_type = await crud_service.get(id)
        if load_type is None:
            raise ValueError(f"Категория вида груза с ID {id} не найдена")
        return await crud_service.update_obj(session_obj=load_type, obj_in=update_data)  # type: ignore[return-value]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.delete(
    "/{id}",
    dependencies=[Depends(require_permission((Permission.CARGO, Action.EDIT)))],
)
async def delete_load_type(id: int, crud_service: ServiceCRUD) -> Response:
    """Удалить запись по ID из таблицы категорий вида грузов."""
    try:
        await crud_service.delete_obj(id=id)
        return Response(status_code=status.HTTP_200_OK)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except IntegrityError as e:
        if "null value in column" in str(
            e.orig,
        ) and "violates not-null constraint" in str(e.orig):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "На данную категорию существует ссылка."
                    " Категория под запретом для оперции удаления"
                ),
            ) from e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
