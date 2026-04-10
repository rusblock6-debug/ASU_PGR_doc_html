import logging
import os
import time
from typing import Any, Dict

import requests


logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("%s=%r is invalid, using default=%s", name, raw, default)
        return default
    return max(value, minimum)


class BortNotifier:
    @staticmethod
    def notify_vehicle_updated(vehicle_id: int) -> Dict[str, Any]:
        enabled = _env_bool("BORT_NOTIFY_ENABLED", False)
        if not enabled:
            return {"status": "disabled", "reason": "BORT_NOTIFY_ENABLED=false"}

        url_template = os.getenv("BORT_NOTIFY_URL_TEMPLATE", "").strip()
        if not url_template:
            return {"status": "disabled", "reason": "BORT_NOTIFY_URL_TEMPLATE is empty"}

        try:
            notify_url = url_template.format(vehicle_id=vehicle_id)
        except Exception as exc:
            logger.error("Invalid BORT_NOTIFY_URL_TEMPLATE=%r: %s", url_template, exc)
            return {"status": "error", "message": str(exc)}

        timeout_sec = _env_int("BORT_NOTIFY_TIMEOUT_SEC", 5, minimum=1)
        max_attempts = _env_int("BORT_NOTIFY_MAX_ATTEMPTS", 3, minimum=1)
        retry_delay_sec = _env_int("BORT_NOTIFY_RETRY_DELAY_SEC", 2, minimum=0)
        force = _env_bool("BORT_NOTIFY_FORCE", False)

        last_error = ""
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.post(
                    notify_url,
                    params={"force": str(force).lower()},
                    timeout=timeout_sec,
                )
                response.raise_for_status()
                logger.info(
                    "Notified settings-bort for vehicle_id=%s, url=%s, status=%s, attempt=%s",
                    vehicle_id,
                    notify_url,
                    response.status_code,
                    attempt,
                )
                return {
                    "status": "success",
                    "url": notify_url,
                    "attempt": attempt,
                    "status_code": response.status_code,
                }
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Notify settings-bort failed for vehicle_id=%s (attempt %s/%s): %s",
                    vehicle_id,
                    attempt,
                    max_attempts,
                    exc,
                )
                if attempt < max_attempts and retry_delay_sec > 0:
                    time.sleep(retry_delay_sec)

        return {
            "status": "error",
            "url": notify_url,
            "message": last_error or "notify failed",
            "attempts": max_attempts,
        }
