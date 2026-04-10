import asyncio
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.utils.settings_manager import SettingsManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
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
        logger.warning(f"{name}={raw!r} is invalid, using default={default}")
        return default
    return max(value, minimum)


async def _auto_init_loop(
    vehicle_id: str,
    settings_url: str,
    retry_interval_sec: int,
    max_attempts: int,
) -> None:
    settings_manager = SettingsManager()
    attempt = 0

    while True:
        attempt += 1
        logger.info(f"AUTO_INIT: attempt {attempt} for VEHICLE_ID={vehicle_id}")
        ok = await settings_manager.init_with_vehicle_id(
            vehicle_id=vehicle_id,
            settings_url=settings_url,
        )
        if ok:
            logger.info(f"AUTO_INIT: successfully initialized VEHICLE_ID={vehicle_id}")
            return

        if max_attempts > 0 and attempt >= max_attempts:
            logger.error(
                "AUTO_INIT: reached max attempts "
                f"({max_attempts}) for VEHICLE_ID={vehicle_id}"
            )
            return

        logger.warning(
            "AUTO_INIT: init failed, retrying in "
            f"{retry_interval_sec}s for VEHICLE_ID={vehicle_id}"
        )
        await asyncio.sleep(retry_interval_sec)


async def _auto_sync_loop(
    vehicle_id: str,
    settings_url: str,
    interval_sec: int,
    force_on_start: bool,
) -> None:
    settings_manager = SettingsManager()
    first_iteration = True

    while True:
        force = force_on_start and first_iteration
        first_iteration = False

        result = await settings_manager.sync_with_vehicle_id(
            vehicle_id=vehicle_id,
            settings_url=settings_url,
            force=force,
        )

        status = result.get("status")
        if status == "updated":
            logger.info(
                "AUTO_SYNC: settings updated for VEHICLE_ID=%s, checksum=%s",
                vehicle_id,
                result.get("checksum", "")[:12],
            )
        elif status == "no_change":
            logger.debug("AUTO_SYNC: no changes for VEHICLE_ID=%s", vehicle_id)
        else:
            logger.warning(
                "AUTO_SYNC: sync failed for VEHICLE_ID=%s: %s",
                vehicle_id,
                result.get("message", "unknown error"),
            )

        await asyncio.sleep(interval_sec)


@asynccontextmanager
async def lifespan(app: FastAPI):
    background_tasks: list[asyncio.Task] = []

    # 1. SQLite schema init
    try:
        logger.info("Starting local SQLite schema initialization...")

        from app.database.init_db import init_schema

        await asyncio.to_thread(init_schema)
        logger.info("Local SQLite schema initialization completed successfully")
    except Exception as e:
        logger.error(f"Failed to initialize local SQLite schema: {e}")
        logger.exception("Database init error details")
        raise

    # 2. Check settings
    all_settings = {}
    try:
        sm = SettingsManager()
        all_settings = await sm.get_all_settings()

        if not all_settings:
            logger.warning("No settings found in database. Initialization required.")
        else:
            logger.info(f"Settings loaded from database: {list(all_settings.keys())}")

    except Exception as e:
        logger.error(f"Failed to initialize SettingsManager: {e}")

    auto_init_enabled = _env_bool("AUTO_INIT_ENABLED", False)
    auto_init_vehicle_id = (
        os.getenv("AUTO_INIT_VEHICLE_ID", "").strip()
        or os.getenv("VEHICLE_ID", "").strip()
    )
    auto_init_retry_interval_sec = _env_int("AUTO_INIT_RETRY_INTERVAL_SEC", 30, minimum=1)
    auto_init_max_attempts = _env_int("AUTO_INIT_MAX_ATTEMPTS", 0, minimum=0)
    auto_init_force = _env_bool("AUTO_INIT_FORCE", False)
    auto_init_settings_url = os.getenv("SETTINGS_URL", "").strip()
    auto_sync_enabled = _env_bool("AUTO_SYNC_ENABLED", True)
    auto_sync_vehicle_id = os.getenv("AUTO_SYNC_VEHICLE_ID", "").strip() or auto_init_vehicle_id
    auto_sync_interval_sec = _env_int("AUTO_SYNC_INTERVAL_SEC", auto_init_retry_interval_sec, minimum=1)
    auto_sync_force_on_start = _env_bool("AUTO_SYNC_FORCE_ON_START", auto_init_force)
    auto_sync_settings_url = os.getenv("AUTO_SYNC_SETTINGS_URL", "").strip()

    if auto_sync_enabled:
        if not auto_sync_vehicle_id:
            logger.warning("AUTO_SYNC is enabled but VEHICLE_ID is empty, skipping auto sync")
        else:
            background_tasks.append(
                asyncio.create_task(
                    _auto_sync_loop(
                        vehicle_id=auto_sync_vehicle_id,
                        settings_url=auto_sync_settings_url,
                        interval_sec=auto_sync_interval_sec,
                        force_on_start=auto_sync_force_on_start,
                    )
                )
            )
    elif auto_init_enabled:
        if not auto_init_vehicle_id:
            logger.warning("AUTO_INIT is enabled but VEHICLE_ID is empty, skipping auto init")
        elif all_settings and not auto_init_force:
            logger.info("AUTO_INIT skipped: local settings already exist (set AUTO_INIT_FORCE=true to override)")
        else:
            background_tasks.append(
                asyncio.create_task(
                    _auto_init_loop(
                        vehicle_id=auto_init_vehicle_id,
                        settings_url=auto_init_settings_url,
                        retry_interval_sec=auto_init_retry_interval_sec,
                        max_attempts=auto_init_max_attempts,
                    )
                )
            )

    try:
        yield
    finally:
        for task in background_tasks:
            if task.done():
                continue
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info("Background task cancelled")



app = FastAPI(
    title="Settings Service",
    description="Бортовой сервис для управления настройками и переменными окружения",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

static_dir = Path(__file__).resolve().parent / "app" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# --- Роутеры ---
from app.routers.settings import settings_router
from app.routers.vehicle import vehicle_router
from app.routers.admin import admin_router, admin_api_router

app.include_router(settings_router, prefix='/api')
app.include_router(vehicle_router, prefix='/api')
app.include_router(admin_router)
app.include_router(admin_api_router, prefix='/api')


@app.get("/")
def read_root():
    return {"status": "working"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8007,
        reload=True,
    )
