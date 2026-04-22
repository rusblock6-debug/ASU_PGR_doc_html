"""Ручки для полной синхронизации данных (сервер - борт)."""

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.sync_service import SyncService
from app.utils.dependencies import get_db_session

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/full")
async def export_full_snapshot(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Полная выгрузка данных (используется бортом для первичной/повторной синхронизации)."""
    snapshot = await SyncService.export_full_snapshot(db)
    return snapshot


@router.post("/pull", status_code=status.HTTP_202_ACCEPTED)
async def pull_snapshot_from_server(
    server_base_url: str | None = Body(
        None,
        embed=True,
        description="Базовый URL сервера (перекрывает настройку SERVER_SYNC_BASE_URL)",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Запустить синхронизацию на борту вручную."""
    if settings.DEPLOYMENT_MODE.lower() != "board":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pull доступен только в режиме DEPLOYMENT_MODE=board",
        )

    base_url = server_base_url or settings.SERVER_SYNC_BASE_URL
    if not base_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SERVER_SYNC_BASE_URL не задан",
        )

    summary = await SyncService.sync_from_server(
        db=db,
        base_url=base_url,
        export_path=settings.SYNC_EXPORT_PATH,
        timeout=settings.SYNC_HTTP_TIMEOUT,
    )

    logger.info(
        "Manual board sync completed",
        summary=summary,
        base_url=base_url,
        export_path=settings.SYNC_EXPORT_PATH,
    )
    return {"status": "synced", "summary": summary}
