from fastapi import APIRouter

from app.utils.vehicle_request import get_vehicles_from_enterprise

vehicle_router = APIRouter(tags=["Vehicle"], prefix='/vehicle')


@vehicle_router.get("")
async def get_active_vehicle():
    vehicles_data = await get_vehicles_from_enterprise()
    result = [{"vehicle_id": item["id"]} for item in vehicles_data["items"]]
    return result
