"""Операции для map_settings."""

from auth_lib import Action, Permission, require_permission
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.map_settings import (
    MapSettingsResponse,
    MapSettingValueResponse,
    MapSettingValueUpdate,
)
from app.services.map_settings import map_setting_service
from config.database import get_async_db

map_setting_router = APIRouter(prefix="/map-settings", tags=["Map Settings"])


@map_setting_router.get(
    "",
    response_model=MapSettingsResponse,
    dependencies=[Depends(require_permission((Permission.MAP, Action.VIEW)))],
)
async def list_map_settings(db: AsyncSession = Depends(get_async_db)):
    return await map_setting_service.list_settings(db=db)


@map_setting_router.get(
    "/{setting_name}",
    response_model=MapSettingValueResponse,
    dependencies=[Depends(require_permission((Permission.MAP, Action.VIEW)))],
)
async def get_map_setting(setting_name: str, db: AsyncSession = Depends(get_async_db)):
    try:
        return await map_setting_service.get_setting(db=db, setting_name=setting_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@map_setting_router.patch(
    "/{setting_name}",
    response_model=MapSettingValueResponse,
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def patch_map_setting(
    setting_name: str,
    payload: MapSettingValueUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await map_setting_service.update_setting(
            db=db,
            setting_name=setting_name,
            payload=payload,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
