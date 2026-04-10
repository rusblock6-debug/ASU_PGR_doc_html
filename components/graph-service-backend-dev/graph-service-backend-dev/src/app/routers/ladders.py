"""CRUD операции для лестничных узлов (ladder)"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.ladders import (
    LadderConnect,
    LadderCreate,
    LadderListResponse,
    LadderResponse,
    LadderUpdate,
)
from app.services.ladders import ladder_service
from config.database import get_async_db

logger = logging.getLogger(__name__)

ladder_router = APIRouter(prefix="/ladders", tags=["Ladders"])
ladder_nodes_router = APIRouter(prefix="/ladder-nodes", tags=["Ladder nodes"])


@ladder_router.get("", response_model=LadderListResponse)
async def get_ladders(
    page: int | None = Query(None, ge=1, description="Номер страницы (опционально)"),
    size: int | None = Query(None, ge=1, le=100, description="Размер страницы (опционально)"),
    db: AsyncSession = Depends(get_async_db),
):
    return await ladder_service.get_ladders(db, page, size)


@ladder_router.get("/{ladder_id}", response_model=LadderResponse)
async def get_ladder(ladder_id: int, db: AsyncSession = Depends(get_async_db)):
    try:
        return await ladder_service.get_ladder(db, ladder_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@ladder_router.post("", response_model=LadderResponse, status_code=status.HTTP_201_CREATED)
async def create_ladder(ladder_data: LadderCreate, db: AsyncSession = Depends(get_async_db)):
    try:
        return await ladder_service.create_ladder(db, ladder_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@ladder_router.patch("/{ladder_id}", response_model=LadderResponse)
async def patch_ladder(
    ladder_id: int,
    ladder_data: LadderUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await ladder_service.update_ladder(db, ladder_id, ladder_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@ladder_router.delete("/{ladder_id}")
async def delete_ladder(ladder_id: int, db: AsyncSession = Depends(get_async_db)):
    try:
        return await ladder_service.delete_ladder(db, ladder_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# TODO переосмыслить лестницы, это должна быть отдельная сущность а не просто дорога с пораметром
#  возможно стоит сделать как с транспортом, шасами и пдм
@ladder_nodes_router.delete("/{node_id}")
async def delete_ladder_node(node_id: int, db: AsyncSession = Depends(get_async_db)):
    """Удалить ladder узел и все связанные узлы на других уровнях"""
    try:
        return await ladder_service.delete_ladder_node(db, node_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@ladder_nodes_router.post("/connect", status_code=status.HTTP_201_CREATED)
async def connect_ladder_nodes(data: LadderConnect, db: AsyncSession = Depends(get_async_db)):
    """Создать лестницу между двумя конкретными узлами по их ID"""
    try:
        from_node_id = int(data.from_node_id)
        to_node_id = int(data.to_node_id)

        return await ladder_service.connect_ladder_nodes(db, from_node_id, to_node_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
