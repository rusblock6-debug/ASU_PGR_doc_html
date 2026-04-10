"""CRUD операции для узлов графа (nodes)"""

import logging
from typing import Any

from auth_lib import Action, Permission, require_permission
from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.nodes import NodeCreate, NodePlaceLinksUpdate, NodeResponse
from app.services.nodes import node_service
from config.database import get_async_db

logger = logging.getLogger(__name__)

node_router = APIRouter(prefix="/nodes", tags=["Nodes"])


@node_router.get(
    "/{node_id}",
    response_model=NodeResponse,
    dependencies=[Depends(require_permission((Permission.MAP, Action.VIEW)))],
)
async def get_node(node_id: int, db: AsyncSession = Depends(get_async_db)):
    """Получить узел по ID"""
    try:
        node = await node_service.get_node_by_id(db, node_id)
        logger.debug(f"Retrieved node {node_id} successfully")
        return node
    except ValueError as e:
        logger.warning(f"Node {node_id} not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@node_router.post(
    "",
    response_model=NodeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def create_node(node_data: NodeCreate, db: AsyncSession = Depends(get_async_db)):
    """Создать новый узел графа"""
    try:
        return await node_service.create_node(db, node_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error creating node: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create node: {str(e)}",
        ) from e


@node_router.put(
    "/{node_id}",
    response_model=NodeResponse,
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def update_node(
    node_id: int,
    update_data: dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_async_db),
):
    """Обновить узел графа (позиция, тип и т.д.)"""
    try:
        return await node_service.update_node(db, node_id, update_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@node_router.delete(
    "/{node_id}",
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def delete_node(node_id: int, db: AsyncSession = Depends(get_async_db)):
    """Удалить узел графа"""
    try:
        return await node_service.delete_node(db, node_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@node_router.get(
    "/{node_id}/places",
    dependencies=[Depends(require_permission((Permission.MAP, Action.VIEW)))],
)
async def get_node_places(node_id: int, db: AsyncSession = Depends(get_async_db)):
    try:
        return await node_service.get_node_places(db, node_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@node_router.put(
    "/{node_id}/places",
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def replace_node_places(
    node_id: int,
    body: NodePlaceLinksUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await node_service.replace_node_places(db, node_id, body.place_ids)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@node_router.delete(
    "/{node_id}/places/{place_id}",
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def unlink_node_place(
    node_id: int,
    place_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await node_service.unlink_node_place(db, node_id, place_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
