"""CRUD операции для меток (tags)"""

import logging

from auth_lib import Action, Permission, require_permission
from fastapi import APIRouter, Depends, HTTPException, status
from starlette.responses import Response

from app.schemas.tags import (
    APITagCreateModel,
    APITagResponseModel,
    APITagsResponseModel,
    APITagUpdateModel,
)
from app.services.crud.tags import TagsCRUD
from app.services.locations import loc_finder
from config.database import Session

logger = logging.getLogger(__name__)

tag_router = APIRouter(prefix="/tags", tags=["Tags"])


@tag_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_permission((Permission.TAGS, Action.EDIT), (Permission.MAP, Action.EDIT))),
    ],
)
async def create_tag(tag_data: APITagCreateModel, session: Session):
    """Создать новую метку"""
    try:
        # return await tag_service.create_tag(session, tag_data)
        tag_service = TagsCRUD(session)
        created_tag = await tag_service.create_tag(tag_data)
        await loc_finder.add_db_tags(created_tag.id)  # type: ignore[arg-type]
        return created_tag
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except TypeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error creating tag: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


@tag_router.get(
    "/{tag_id}",
    response_model=APITagResponseModel,
    dependencies=[Depends(require_permission((Permission.TAGS, Action.VIEW)))],
)
async def get_tag(tag_id: int, session: Session):
    """Получить метку по ID"""
    try:
        tag_service = TagsCRUD(session)
        tag = await tag_service.get_by_id(tag_id)
        logger.debug(f"Retrieved tag {tag_id} successfully")
        return tag
    except ValueError as e:
        logger.warning(f"Tag {tag_id} not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@tag_router.get(
    "",
    response_model=APITagsResponseModel,
    dependencies=[Depends(require_permission((Permission.TAGS, Action.VIEW)))],
)
async def get_tags(
    session: Session,
    size: int = 10,
    page: int = 1,
):
    """Получить список меток"""
    try:
        tag_service = TagsCRUD(session)
        total, pages, tags = await tag_service.get_all(size, page)  # type: ignore[misc]
        items = [APITagResponseModel.model_validate(tag) for tag in tags]  # type: ignore[union-attr,attr-defined]
        return APITagsResponseModel(
            page=page,
            pages=int(pages),  # type: ignore[arg-type,call-overload]
            size=len(items),
            total=int(total),  # type: ignore[arg-type,call-overload]
            items=items,
        )
    except ValueError as e:
        logger.warning(f"Tags not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@tag_router.put(
    "/{tag_id}",
    response_model=APITagResponseModel,
    dependencies=[
        Depends(require_permission((Permission.TAGS, Action.EDIT), (Permission.MAP, Action.EDIT))),
    ],
)
async def update_tag(session: Session, tag_id: int, update_data: APITagUpdateModel):
    """Обновить все поля метки"""
    try:
        tag_service = TagsCRUD(session)
        updated_tag = await tag_service.update_tag(tag_id, update_data)
        await loc_finder.update_db_tag(updated_tag.id)  # type: ignore[arg-type]
        return APITagResponseModel.from_orm(updated_tag)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@tag_router.delete(
    "/{tag_id}",
    dependencies=[
        Depends(require_permission((Permission.TAGS, Action.EDIT), (Permission.MAP, Action.EDIT))),
    ],
)
async def delete_tag(tag_id: int, session: Session):
    """Удалить метку"""
    try:
        tag_service = TagsCRUD(session)
        await tag_service.delete_obj(id=tag_id)
        (await loc_finder.remove_db_tag(tag_id),)
        return Response(status_code=status.HTTP_200_OK)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
