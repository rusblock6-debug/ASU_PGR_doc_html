"""CRUD операции для мест (places)"""

import logging

from auth_lib import Action, Permission, require_permission
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.places import (
    PlaceCreate,
    PlaceDeleteResponse,
    PlacePatch,
    PlaceResponse,
    PlacesGroupedResponse,
    PlacesListResponse,
    PlacesPopupResponse,
    PlaceStockUpdate,
    PlaceStockUpdateResponse,
)
from app.services.place_remaining import place_remaining_service
from app.services.places import place_service
from config.database import get_async_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/places", tags=["Places"])


@router.get(
    "",
    response_model=PlacesListResponse,
    dependencies=[
        Depends(
            require_permission(
                (Permission.WORK_TIME_MAP, Action.VIEW),
                (Permission.TRIP_EDITOR, Action.VIEW),
                (Permission.WORK_ORDER, Action.VIEW),
                (Permission.PLACES, Action.VIEW),
                (Permission.TAGS, Action.VIEW),
            ),
        ),
    ],
)
async def list_places(
    page: int | None = Query(None, ge=1, description="Номер страницы (опционально)"),
    size: int | None = Query(None, ge=1, le=100, description="Размер страницы (опционально)"),
    type: list[str] | None = Query(None),
    types: str | None = Query(None),
    is_active: str | None = Query(None),
    limit: int | None = Query(None),
    offset: int | None = Query(None),
    db: AsyncSession = Depends(get_async_db),
):
    """Получить список мест (places).

    Если параметры page и size не указаны — возвращает все записи.
    Если указан хотя бы один — применяется пагинация.
    """
    return await place_service.list_places(
        db,
        page,
        size,
        type,
        types,
        is_active,
        limit,
        offset,
    )


# МБ не нужно и групировка будет на фронте
@router.get(
    "/grouped",
    response_model=PlacesGroupedResponse,
    dependencies=[Depends(require_permission((Permission.PLACES, Action.VIEW)))],
)
async def list_places_grouped(
    type: list[str] | None = Query(None),
    types: str | None = Query(None),
    is_active: str | None = Query(None),
    db: AsyncSession = Depends(get_async_db),
):
    """Получить список мест, сгруппированный по типам (для сайдбара редактора).
    Не заменяет и не ломает существующий GET /places.
    """
    return await place_service.list_places_grouped(
        db=db,
        type=type,
        types=types,
        is_active=is_active,
    )


@router.post(
    "",
    response_model=PlaceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            require_permission((Permission.PLACES, Action.EDIT), (Permission.MAP, Action.EDIT)),
        ),
    ],
)
async def create_place(
    body: PlaceCreate = Body(
        ...,
        openapi_examples={
            "load": {
                "summary": "Load place",
                "value": {
                    "type": "load",
                    "name": "Load 1",
                    "node_id": 101,
                    "cargo_type": 1,
                    "start_date": "2026-03-21",
                    "end_date": "2026-04-01",
                    "current_stock": 1500.0,
                },
            },
            "unload": {
                "summary": "Unload place",
                "value": {
                    "type": "unload",
                    "name": "Unload 1",
                    "node_id": 102,
                    "cargo_type": 2,
                    "start_date": "2026-03-21",
                    "end_date": "2026-04-01",
                    "capacity": 5000.0,
                    "current_stock": 900.0,
                },
            },
            "reload": {
                "summary": "Reload place",
                "value": {
                    "type": "reload",
                    "name": "Reload 1",
                    "node_id": 103,
                    "cargo_type": 3,
                    "start_date": "2026-03-21",
                    "capacity": 3000.0,
                    "current_stock": 400.0,
                },
            },
            "park": {
                "summary": "Park place",
                "value": {
                    "type": "park",
                    "name": "Park A",
                    "node_id": 104,
                },
            },
            "transit": {
                "summary": "Transit place",
                "value": {
                    "type": "transit",
                    "name": "Transit A",
                    "node_id": 105,
                },
            },
        },
    ),
    db: AsyncSession = Depends(get_async_db),
):
    """Создать новую точку (Place)."""
    try:
        return await place_service.create_place(db, body)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{place_id}",
    response_model=PlaceResponse,
    dependencies=[Depends(require_permission((Permission.PLACES, Action.VIEW)))],
)
async def get_place(place_id: int, db: AsyncSession = Depends(get_async_db)):
    """Получить Place по ID"""
    try:
        return await place_service.get_place(db, place_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.patch(
    "/{place_id}",
    response_model=PlaceResponse,
    dependencies=[
        Depends(
            require_permission((Permission.PLACES, Action.EDIT), (Permission.MAP, Action.EDIT)),
        ),
    ],
)
async def update_place(
    place_id: int,
    body: PlacePatch = Body(
        ...,
        openapi_examples={
            "stock_only": {
                "summary": "Только остаток (тип из БД)",
                "value": {"current_stock": 1200.0, "source": "system"},
            },
            "load": {
                "summary": "Load place",
                "value": {
                    "type": "load",
                    "name": "Load 1 (updated)",
                    "node_id": 101,
                    "start_date": "2026-03-21",
                    "end_date": "2026-04-01",
                    "current_stock": 1200.0,
                },
            },
            "unload": {
                "summary": "Unload place",
                "value": {
                    "type": "unload",
                    "name": "Unload 1 (updated)",
                    "node_id": 102,
                    "start_date": "2026-03-21",
                    "end_date": "2026-04-01",
                    "capacity": 4500.0,
                    "current_stock": 800.0,
                },
            },
            "reload": {
                "summary": "Reload place",
                "value": {
                    "type": "reload",
                    "name": "Reload 1 (updated)",
                    "node_id": 103,
                    "start_date": "2026-03-21",
                    "capacity": 2800.0,
                    "current_stock": 350.0,
                },
            },
            "park": {
                "summary": "Park place",
                "value": {
                    "type": "park",
                    "name": "Park A (updated)",
                    "node_id": 104,
                },
            },
            "transit": {
                "summary": "Transit place",
                "value": {
                    "type": "transit",
                    "name": "Transit A (updated)",
                    "node_id": 105,
                },
            },
        },
    ),
    db: AsyncSession = Depends(get_async_db),
):
    """Частичное обновление Place."""
    try:
        return await place_service.update_place(db, place_id, body)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/{place_id}/stock",
    response_model=PlaceStockUpdateResponse,
    status_code=status.HTTP_200_OK,
)
async def update_place_stock(
    place_id: int,
    body: PlaceStockUpdate = Body(
        ...,
        openapi_examples={
            "loading": {
                "summary": "Погрузка (увеличить остаток)",
                "value": {"change_type": "loading", "change_amount": 100.0},
            },
            "unloading": {
                "summary": "Разгрузка (уменьшить остаток)",
                "value": {"change_type": "unloading", "change_amount": -50.0},
            },
            "initial": {
                "summary": "Инициализация остатка (дельта)",
                "value": {"change_type": "initial", "change_amount": 1000.0},
            },
        },
    ),
    db: AsyncSession = Depends(get_async_db),
):
    """Обновить остатки на месте.
    Вызывается из trip-service при изменении остатков.
    """
    result = await place_remaining_service.update_place_stock(
        db,
        place_id,
        body.change_type,
        body.change_amount,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update place stock",
        )
    return {"status": "ok"}


@router.delete(
    "/{place_id}",
    response_model=PlaceDeleteResponse,
    dependencies=[
        Depends(
            require_permission((Permission.PLACES, Action.EDIT), (Permission.MAP, Action.EDIT)),
        ),
    ],
)
async def delete_place(place_id: int, db: AsyncSession = Depends(get_async_db)):
    """Удалить Place по ID"""
    try:
        return await place_service.delete_place(db, place_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/popup/{places_id}",
    response_model=PlacesPopupResponse,
    dependencies=[Depends(require_permission((Permission.MAP, Action.VIEW)))],
)
async def get_place_popup(
    places_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> PlacesPopupResponse:
    """Получить попап для места."""
    return await place_service.get_place_popup(
        db=db,
        place_id=places_id,
    )
