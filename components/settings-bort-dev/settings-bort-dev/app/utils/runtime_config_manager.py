import os
from typing import Any, Dict, Optional, Tuple

import requests
from sqlalchemy import select

from app.database import SessionLocal
from app.models.runtime_config_model import RuntimeConfig


class RuntimeConfigManager:
    @staticmethod
    def _normalize_url(url: str) -> str:
        return url.strip().rstrip("/")

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        settings_url = os.getenv("SETTINGS_URL", "http://host.docker.internal:8006")
        enterprise_server_url = os.getenv("ENTERPRISE_SERVER_URL", "http://host.docker.internal:8002")

        return {
            "settings_url": RuntimeConfigManager._normalize_url(settings_url),
            "enterprise_server_url": RuntimeConfigManager._normalize_url(enterprise_server_url),
        }

    async def get_latest_config(self) -> Dict[str, Any]:
        async with SessionLocal() as session:
            result = await session.execute(
                select(RuntimeConfig).order_by(RuntimeConfig.id.desc()).limit(1)
            )
            record = result.scalar_one_or_none()

            if not record:
                return self.get_default_config()

            return {
                "settings_url": record.settings_url,
                "enterprise_server_url": record.enterprise_server_url,
            }

    async def save_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        settings_url = self._normalize_url(payload["settings_url"])
        enterprise_server_url = self._normalize_url(payload["enterprise_server_url"])

        async with SessionLocal() as session:
            result = await session.execute(
                select(RuntimeConfig).order_by(RuntimeConfig.id.desc()).limit(1)
            )
            record = result.scalar_one_or_none()
            if record is None:
                record = RuntimeConfig(
                    settings_url=settings_url,
                    enterprise_server_url=enterprise_server_url,
                )
                session.add(record)
            else:
                record.settings_url = settings_url
                record.enterprise_server_url = enterprise_server_url

            await session.commit()

        return {
            "settings_url": settings_url,
            "enterprise_server_url": enterprise_server_url,
        }

    async def get_settings_url(self) -> str:
        config = await self.get_latest_config()
        return config["settings_url"]

    async def get_enterprise_server_url(self) -> str:
        config = await self.get_latest_config()
        return config["enterprise_server_url"]

    @staticmethod
    def _probe_url(base_url: str, candidates: list[str]) -> Tuple[bool, Optional[str]]:
        url = RuntimeConfigManager._normalize_url(base_url)
        last_error: Optional[str] = None
        for suffix in candidates:
            endpoint = f"{url}{suffix}"
            try:
                response = requests.get(endpoint, timeout=5)
                response.raise_for_status()
                return True, None
            except Exception as exc:
                last_error = str(exc)
        return False, last_error

    @staticmethod
    def test_settings_server(settings_url: str) -> Tuple[bool, Optional[str]]:
        return RuntimeConfigManager._probe_url(settings_url, ["/api/secrets", "/"])

    @staticmethod
    def test_enterprise_server(enterprise_server_url: str) -> Tuple[bool, Optional[str]]:
        return RuntimeConfigManager._probe_url(enterprise_server_url, ["/api/vehicles", "/"])
