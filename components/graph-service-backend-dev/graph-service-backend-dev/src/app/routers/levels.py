"""Роутер для совместимости с frontend - перенаправляет /api/levels на /api/horizons"""

import logging

from auth_lib import Action, Permission, require_permission
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.horizons import HorizonCreate, HorizonListResponse, HorizonResponse
from app.services.horizons import horizon_service
from config.database import get_async_db

logger = logging.getLogger(__name__)

levels_router = APIRouter(prefix="/levels", tags=["Levels (Legacy)"])


@levels_router.get(
    "",
    response_model=HorizonListResponse,
    dependencies=[Depends(require_permission((Permission.MAP, Action.VIEW)))],
)
async def get_levels(
    page: int | None = Query(None, ge=1, description="Номер страницы (опционально)"),
    size: int | None = Query(None, ge=1, le=100, description="Размер страницы (опционально)"),
    db: AsyncSession = Depends(get_async_db),
):
    """Получить список всех уровней (перенаправлено на horizons)."""
    return await horizon_service.get_horizons(db, page, size)


@levels_router.post(
    "",
    response_model=HorizonResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def create_level(level_data: dict, db: AsyncSession = Depends(get_async_db)):
    """Создать новый уровень (перенаправлено на horizons).
    Принимает данные в формате frontend и преобразует в HorizonCreate.
    """
    try:
        # Преобразуем данные из формата frontend в формат backend
        name = level_data.get("name")
        height = level_data.get("height")
        if name is None or height is None:
            raise ValueError("name and height are required")
        horizon_data = HorizonCreate(
            name=name,
            height=height,
            color=level_data.get("color", "#2196F3"),
            id=level_data.get("id"),
            shafts=level_data.get("shafts", []),
        )

        # Игнорируем поле description, если оно есть
        return await horizon_service.create_horizon(db, horizon_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error creating level: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@levels_router.get(
    "/{level_id}",
    response_model=HorizonResponse,
    dependencies=[Depends(require_permission((Permission.MAP, Action.VIEW)))],
)
async def get_level(level_id: int, db: AsyncSession = Depends(get_async_db)):
    """Получить уровень по ID (перенаправлено на horizons)."""
    try:
        return await horizon_service.get_horizon(db, level_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@levels_router.get(
    "/{level_id}/graph/count",
    dependencies=[Depends(require_permission((Permission.MAP, Action.VIEW)))],
)
async def get_level_objects_count(level_id: int, db: AsyncSession = Depends(get_async_db)):
    """Получить количество объектов на уровне (перенаправлено на horizons)."""
    try:
        return await horizon_service.get_horizon_objects_count(db, level_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@levels_router.delete(
    "/{level_id}",
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def delete_level(level_id: int, db: AsyncSession = Depends(get_async_db)):
    """Удалить уровень со всеми объектами (перенаправлено на horizons)."""
    try:
        return await horizon_service.delete_horizon(db, level_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@levels_router.get(
    "/{level_id}/graph",
    dependencies=[Depends(require_permission((Permission.MAP, Action.VIEW)))],
)
async def get_level_graph(level_id: int, db: AsyncSession = Depends(get_async_db)):
    """Получить полный граф уровня (перенаправлено на horizons)."""
    try:
        return await horizon_service.get_horizon_graph(db, level_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@levels_router.post(
    "/{level_id}/ladder-nodes",
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def create_ladder_node(
    level_id: int,
    ladder_data: dict,
    db: AsyncSession = Depends(get_async_db),
):
    """Создать ladder узел (перенаправлено на horizons)."""
    try:
        from app.services.ladders import ladder_service

        return await ladder_service.create_ladder_node(db, level_id, ladder_data)  # type: ignore[attr-defined]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@levels_router.get(
    "/{level_id}/ladder-nodes",
    dependencies=[Depends(require_permission((Permission.MAP, Action.VIEW)))],
)
async def get_ladder_nodes(level_id: int, db: AsyncSession = Depends(get_async_db)):
    """Получить все ladder узлы на уровне (перенаправлено на horizons)."""
    try:
        from app.services.ladders import ladder_service

        return await ladder_service.get_ladder_nodes(db, level_id)  # type: ignore[attr-defined]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
