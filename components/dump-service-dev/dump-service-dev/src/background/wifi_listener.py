# ruff: noqa: D100, D101
import asyncio
import threading
from multiprocessing import Process
from pathlib import Path
from uuid import uuid4

from botocore.exceptions import EndpointConnectionError
from loguru import logger
from paho.mqtt import client as mqtt_client

from src.app.controller import FileController
from src.app.factory import Factory
from src.app.model import File as FileModel
from src.app.scheme import mqtt_event
from src.app.type import SyncStatus, WifiStatus
from src.core.config import get_settings
from src.core.database import db_session
from src.core.database.postgres.dependency.session import PostgresSession
from src.core.database.postgres.session import reset_session_context, set_session_context
from src.core.exception import NotFoundException
from src.core.mqtt_broker import MQTTApp, MQTTRouter
from src.core.s3 import S3Client, get_s3_client

settings = get_settings()
router = MQTTRouter()
# Храним в памяти процесса статус.
wifi_status: WifiStatus | None = None

_UPLOAD_IDLE_SLEEP_SECONDS = 60
_UPLOAD_BUCKET_NAME = "dump-service"
_stop_upload_event = threading.Event()
_upload_thread: threading.Thread | None = None
_upload_thread_lock = threading.Lock()


async def _process_next_batch(factory: Factory, s3_client: S3Client) -> bool:
    context = set_session_context(str(uuid4()))
    session_dependency = PostgresSession(db_session=db_session)
    try:
        async with session_dependency as session:
            file_controller = FileController(
                file_repository=factory.file_repository(db_session=session),
                exclude_fields=settings.EXCLUDE_FIELDS,
            )

            files = await _load_unsynced_files(file_controller)
            if not files:
                return False

            return await _upload_files(file_controller, files, s3_client)
    finally:
        reset_session_context(context)


async def _load_unsynced_files(file_controller: FileController) -> list[FileModel]:
    try:
        file_response = await file_controller.get_unsync_files()
    except NotFoundException:
        return []
    return file_response.data or []


async def _upload_files(
    file_controller: FileController,
    files: list[FileModel],
    s3_client: S3Client,
) -> bool:
    for file in files:
        if _stop_upload_event.is_set():
            logger.info("Wi-Fi disabled mid-transfer, stopping batch")
            return True

        if not await _process_single_file(file_controller, file, s3_client):
            return False

    return True


async def _process_single_file(
    file_controller: FileController,
    file: FileModel,
    s3_client: S3Client,
) -> bool:
    path = Path(file.path)
    s3_key = _build_s3_key(path)
    try:
        await s3_client.upload_file_stream(
            s3_key,
            path,
            ensure_unique=False,
        )
    except EndpointConnectionError:
        logger.error("endpoint s3 connection error")
        return True
    except FileNotFoundError:
        logger.error("file not found: {path}", path=path.name)
        await file_controller.delete_by_id(file.id)
        return True
    except Exception as exc:
        logger.exception(exc)
        return False

    file.sync_status = SyncStatus.SYNCED
    _remove_local_file(path)
    return True


def _build_s3_key(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(settings.DUMP_STORAGE_DIR.resolve())
        return relative.as_posix()
    except Exception:
        return f"{path.parts[-2]}/{path.name}"


def _remove_local_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=False)
        logger.debug("file delete  {file}", file=path.name)
    except FileNotFoundError:
        logger.warning("local dump already removed after upload: {path}", path=path)
    except PermissionError:
        logger.error("cannot remove local dump file (permission denied): {path}", path=path)
    except Exception:
        logger.exception("failed to remove local dump file {path}", path=path)


async def _upload_worker() -> None:
    logger.info("Wi-Fi enabled, starting upload thread loop")
    factory = Factory()
    s3_client = get_s3_client(bucket_name=_UPLOAD_BUCKET_NAME)
    try:
        while not _stop_upload_event.is_set():
            has_files = await _process_next_batch(factory, s3_client)
            if not has_files:
                await asyncio.sleep(_UPLOAD_IDLE_SLEEP_SECONDS)
    finally:
        logger.info("Upload thread loop finished")


def _upload_thread_entry() -> None:
    try:
        asyncio.run(_upload_worker())
    except Exception:
        logger.exception("Uploader thread crashed")
    finally:
        global _upload_thread
        with _upload_thread_lock:
            _upload_thread = None


def _start_upload_thread() -> None:
    global _upload_thread
    with _upload_thread_lock:
        if _upload_thread and _upload_thread.is_alive():
            logger.debug("Upload thread already running")
            return

        _stop_upload_event.clear()
        thread = threading.Thread(
            target=_upload_thread_entry,
            name="wifi-upload-thread",
        )
        _upload_thread = thread
        thread.start()


async def _stop_upload_thread() -> None:
    global _upload_thread
    thread = None
    with _upload_thread_lock:
        thread = _upload_thread

    if not thread:
        return

    _stop_upload_event.set()
    if thread.is_alive():
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, thread.join)

    with _upload_thread_lock:
        if _upload_thread is thread:
            _upload_thread = None


@router.subscriber(f"/truck/{settings.TRUCK_ID}/wifi/events")
async def wifi_events(
    payload: mqtt_event.WifiEvent,
    _topic: str,
    _qos: int,
    _msg: mqtt_client.MQTTMessage,
) -> None:
    """Log Wi-Fi listener events for observability."""
    global wifi_status
    logger.info(payload)

    if payload.status == wifi_status:
        logger.debug("Wi-Fi status unchanged: {}", payload.status)
        return

    wifi_status = payload.status

    if wifi_status is WifiStatus.OFF:
        logger.info("Wi-Fi disabled, stopping uploader thread")
        await _stop_upload_thread()
        return

    logger.info("Wi-Fi enabled, starting uploader thread")
    _start_upload_thread()


def _setup_mqtt_app() -> None:
    app = MQTTApp(client_prefix="wifi-listener")
    app.include_router(router)
    app.setup()


def _worker() -> None:
    global wifi_status
    logger.info("Launching uploader worker with NanoMQ integration")
    if settings.WIFI_STATUS:
        wifi_status = WifiStatus.ON
        _start_upload_thread()

    _setup_mqtt_app()


def create_wifi_listener() -> Process:
    """Create a Wi-Fi listener worker process."""
    return Process(target=_worker, name="background-wifi-listener")
