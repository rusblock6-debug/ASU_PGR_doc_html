from typing import Dict, Any
import logging
from fastapi import APIRouter, BackgroundTasks, Body, HTTPException
from app.utils.vault_client import VaultClient
from app.utils.bort_notifier import BortNotifier
from app.utils.initial_reading_secrets import extract_common_variables
from app.schemas.settings import VariableCreateRequest

settings_router = APIRouter(tags=["Settings"], prefix='/secrets')

logger = logging.getLogger(__name__)

@settings_router.post("/{vehicle_id}")
async def create_new_secrets_pack(
    vehicle_id: int,
    background_tasks: BackgroundTasks,
    custom_variables: VariableCreateRequest = Body(...)
):
    try:
        result = VaultClient.create_new_secrets(vehicle_id, custom_variables)
        background_tasks.add_task(BortNotifier.notify_vehicle_updated, vehicle_id)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing config for vehicle_id {vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing configuration: {str(e)}")


@settings_router.get("/{vehicle_id}")
async def read_secrets_pack_by_vehicle_id(
    vehicle_id: int
):
    try:
        return VaultClient.read_secrets_by_vehicle_id(vehicle_id)
    except Exception as e:
        logger.error(f"Error processing config for vehicle_id {vehicle_id}: {e}")
        raise HTTPException(status_code=404, detail=f"Not found config for vehicle_id {vehicle_id}")


@settings_router.delete("/{vehicle_id}")
async def delete_secrets_pack_by_vehicle_id(
    vehicle_id: int
):
    try:
        if VaultClient.delete_secrets_by_vehicle_id(vehicle_id):
            return {"status": "success", "deleted env for vehicle_id": vehicle_id}
    except Exception as e:
        logger.error(f"Error processing config for vehicle_id {vehicle_id}: {e}")
        raise HTTPException(status_code=404, detail=f"Not found config for vehicle_id {vehicle_id}")


@settings_router.get("")
async def get_template():
    result = extract_common_variables()
    return {
        "specific": result["specific"],
        "vehicle_dependant": result["vehicle_dependant"]
    }
