"""Сервис для операций с map_settings."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import MapSetting
from app.schemas.map_settings import (
    MapSettingsResponse,
    MapSettingValueResponse,
    MapSettingValueUpdate,
)


class MapSettingService:
    SETTINGS_MAP = {
        "RoutesColor": "routes_color",
    }

    async def list_settings(self, db: AsyncSession) -> MapSettingsResponse:
        setting = await self._get_or_create_settings_row(db)
        return MapSettingsResponse.model_validate(setting)

    async def get_setting(self, db: AsyncSession, setting_name: str) -> MapSettingValueResponse:
        setting = await self._get_or_create_settings_row(db)
        column_name = self._resolve_setting_column(setting_name)
        return MapSettingValueResponse(
            setting_name=setting_name,
            value=getattr(setting, column_name),
        )

    async def update_setting(
        self,
        db: AsyncSession,
        setting_name: str,
        payload: MapSettingValueUpdate,
    ) -> MapSettingValueResponse:
        setting = await self._get_or_create_settings_row(db)
        column_name = self._resolve_setting_column(setting_name)
        setattr(setting, column_name, payload.value)

        await db.commit()
        await db.refresh(setting)
        return MapSettingValueResponse(
            setting_name=setting_name,
            value=getattr(setting, column_name),
        )

    def _resolve_setting_column(self, setting_name: str) -> str:
        try:
            return self.SETTINGS_MAP[setting_name]
        except KeyError as exc:
            raise ValueError(f"Map setting '{setting_name}' is not supported") from exc

    async def _get_or_create_settings_row(self, db: AsyncSession) -> MapSetting:
        setting = await db.scalar(select(MapSetting).order_by(MapSetting.id).limit(1))
        if setting:
            return setting

        setting = MapSetting()
        db.add(setting)
        await db.commit()
        await db.refresh(setting)
        return setting


map_setting_service = MapSettingService()
