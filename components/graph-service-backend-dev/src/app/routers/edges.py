"""CRUD операции для рёбер графа (edges)"""

import logging
from typing import Any

from auth_lib import Action, Permission, require_permission
from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.edges import (
    EdgeBatchDeleteRequest,
    EdgeBatchUpdateRequest,
    EdgeCreate,
    EdgeResponse,
    EdgeSplitRequest,
)
from app.services.edges import edge_service
from config.database import get_async_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edges", tags=["Edges"])


@router.get(
    "/{edge_id}",
    response_model=EdgeResponse,
    dependencies=[Depends(require_permission((Permission.MAP, Action.VIEW)))],
)
async def get_edge(edge_id: int, db: AsyncSession = Depends(get_async_db)):
    """Получить ребро по ID"""
    try:
        edge = await edge_service.get_edge_by_id(db, edge_id)
        logger.debug(f"Retrieved edge {edge_id} successfully")
        return edge
    except ValueError as e:
        logger.warning(f"Edge {edge_id} not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post(
    "",
    response_model=EdgeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def create_edge(edge_data: EdgeCreate, db: AsyncSession = Depends(get_async_db)):
    """Создать новое ребро графа"""
    try:
        return await edge_service.create_edge(db, edge_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.put(
    "/{edge_id}",
    response_model=EdgeResponse,
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def update_edge(
    edge_id: int,
    update_data: dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_async_db),
):
    """Обновить ребро графа.

    Поддерживает изменение from_node_id, to_node_id, edge_type, weight.
    """
    try:
        return await edge_service.update_edge(db, edge_id, update_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete(
    "/{edge_id}",
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def delete_edge(edge_id: int, db: AsyncSession = Depends(get_async_db)):
    """Удалить ребро графа"""
    try:
        return await edge_service.delete_edge(db, edge_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/{edge_id}/split",
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def split_edge(
    edge_id: int,
    body: EdgeSplitRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """Разрезать ребро в указанной точке:
    создает новый узел и заменяет исходное ребро двумя новыми.
    """
    try:
        return await edge_service.split_edge(
            db=db,
            edge_id=edge_id,
            x=body.x,
            y=body.y,
            node_type=body.node_type,
            node_id=body.node_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.patch(
    "/batch",
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def batch_update_edges(
    body: EdgeBatchUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await edge_service.batch_update_edges(
            db=db,
            items=[item.model_dump(exclude_unset=True) for item in body.items],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete(
    "/batch",
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def batch_delete_edges(
    body: EdgeBatchDeleteRequest,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await edge_service.batch_delete_edges(db=db, edge_ids=body.ids)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
