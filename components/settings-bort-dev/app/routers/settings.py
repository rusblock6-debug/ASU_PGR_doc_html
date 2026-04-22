import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.utils.settings_manager import SettingsManager

settings_router = APIRouter(tags=["Settings"], prefix='/secrets')


@settings_router.post("/init/{vehicle_id}")
async def initialize_settings(
    vehicle_id: str,
    settings_url: Optional[str] = Query(default=None, description="URL settings-server"),
):
    """
    Инициализирует настройки для указанного vehicle_id.
    """
    settings_manager = SettingsManager()
    success = await settings_manager.init_with_vehicle_id(
        vehicle_id=vehicle_id,
        settings_url=settings_url or "",
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to load settings from server")

    export_result = {}
    output_path = os.getenv("BORT_ENV_OUTPUT_PATH", "").strip()
    if output_path:
        export_result = await settings_manager.export_settings_to_env_file(output_path)

    return {
        "status": "success",
        "vehicle_id": vehicle_id,
        "message": "Settings initialized successfully",
        "export": export_result,
    }


@settings_router.get("")
async def get_secrets():
    return await SettingsManager().get_all_settings()
