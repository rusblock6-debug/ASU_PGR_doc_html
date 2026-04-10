import asyncio
import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.schemas.runtime_config import RuntimeConfigPayload
from app.utils.runtime_config_manager import RuntimeConfigManager
from app.utils.settings_manager import SettingsManager
from app.utils.vehicle_request import get_vehicles_from_enterprise


admin_router = APIRouter(tags=["Admin"])
admin_api_router = APIRouter(tags=["Admin API"], prefix="/admin")

_TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "html_templates" / "admin.html"


@admin_router.get("/admin", response_class=HTMLResponse)
async def admin_page() -> HTMLResponse:
    if not _TEMPLATE_PATH.exists():
        raise HTTPException(status_code=500, detail="admin.html template not found")
    return HTMLResponse(_TEMPLATE_PATH.read_text(encoding="utf-8"))


@admin_api_router.get("/config")
async def get_runtime_config() -> Dict[str, Any]:
    return await RuntimeConfigManager().get_latest_config()


@admin_api_router.post("/config")
async def save_runtime_config(payload: RuntimeConfigPayload) -> Dict[str, Any]:
    return await RuntimeConfigManager().save_config(payload.model_dump())


@admin_api_router.post("/test-connections")
async def test_connections(payload: RuntimeConfigPayload) -> Dict[str, Any]:
    manager = RuntimeConfigManager()
    config = payload.model_dump()
    settings_ok, settings_error = await asyncio.to_thread(
        manager.test_settings_server,
        config["settings_url"],
    )
    enterprise_ok, enterprise_error = await asyncio.to_thread(
        manager.test_enterprise_server,
        config["enterprise_server_url"],
    )

    return {
        "settings_server": {"ok": settings_ok, "error": settings_error},
        "enterprise_server": {"ok": enterprise_ok, "error": enterprise_error},
    }


@admin_api_router.post("/init/{vehicle_id}")
async def init_from_admin(vehicle_id: str) -> Dict[str, Any]:
    config = await RuntimeConfigManager().get_latest_config()
    settings_manager = SettingsManager()
    ok = await settings_manager.init_with_vehicle_id(
        vehicle_id=vehicle_id,
        settings_url=config["settings_url"],
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to initialize secrets")
    secrets = await settings_manager.get_all_settings()

    export_result: Dict[str, Any] = {}
    output_path = os.getenv("BORT_ENV_OUTPUT_PATH", "").strip()
    if output_path:
        export_result = await settings_manager.export_settings_to_env_file(output_path)

    return {
        "status": "success",
        "vehicle_id": vehicle_id,
        "secrets_count": len(secrets),
        "export": export_result,
    }


@admin_api_router.post("/sync/{vehicle_id}")
async def sync_from_settings_server(
    vehicle_id: str,
    force: bool = Query(default=False),
) -> Dict[str, Any]:
    config = await RuntimeConfigManager().get_latest_config()
    result = await SettingsManager().sync_with_vehicle_id(
        vehicle_id=vehicle_id,
        settings_url=config["settings_url"],
        force=force,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Sync failed"))
    return result


@admin_api_router.get("/secrets")
async def get_admin_secrets() -> Dict[str, Any]:
    return await SettingsManager().get_all_settings()


@admin_api_router.post("/export-env")
async def export_env_file() -> Dict[str, Any]:
    output_path = os.getenv("BORT_ENV_OUTPUT_PATH", "").strip()
    if not output_path:
        raise HTTPException(status_code=500, detail="BORT_ENV_OUTPUT_PATH is not configured")

    result = await SettingsManager().export_settings_to_env_file(output_path)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Export failed"))
    if result.get("status") == "empty":
        raise HTTPException(status_code=409, detail="No secrets to export. Init is required.")
    return result


@admin_api_router.get("/vehicles")
async def get_vehicle_ids() -> Dict[str, Any]:
    try:
        response = await get_vehicles_from_enterprise()
        items = response.get("items", []) if isinstance(response, dict) else []
        vehicle_ids = [str(item.get("id")) for item in items if item.get("id") is not None]
        return {"vehicle_ids": vehicle_ids, "raw": response}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load vehicles: {exc}")
