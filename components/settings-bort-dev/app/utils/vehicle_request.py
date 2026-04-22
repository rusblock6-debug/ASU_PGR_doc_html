import aiohttp
import os
from dotenv import load_dotenv
from app.utils.runtime_config_manager import RuntimeConfigManager

load_dotenv()


async def get_vehicles_from_enterprise():
    enterprise_server_url = ""
    try:
        enterprise_server_url = await RuntimeConfigManager().get_enterprise_server_url()
    except Exception:
        enterprise_server_url = ""
    if not enterprise_server_url:
        enterprise_server_url = os.getenv('ENTERPRISE_SERVER_URL', '')

    async with aiohttp.ClientSession() as session:
        url = f"{enterprise_server_url}/api/vehicles"
        async with session.get(
                url,
                params={'is_active': 'true'},
                headers={'accept': 'application/json'}
        ) as response:
            data = await response.json()
            return data
