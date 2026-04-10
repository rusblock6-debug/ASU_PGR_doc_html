import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.dependencies import (
    AutorepubConfigManagerDep,
    AutorepubMQTTManagerDep,
    AutorepubRabbitMQManagerDep,
    get_autorepub_config_manager,
    get_autorepub_mqtt_manager,
    get_autorepub_rabbitmq_manager,
)
from app.models.consts import BORT_INSTANCE_ID_PREFIX, SERVER_INSTANCE_ID
from app.models.schemas import AutorepubConfig
from app.models.types import AutorepubConfigType
from app.settings import settings

logger = logging.getLogger("routes.autorepub")

router = APIRouter(prefix="/autorepub", tags=["autorepub"])

# ─────────────────────────────────────────────────────────────────────────
# Config endpoints
# ─────────────────────────────────────────────────────────────────────────

class AutorepubConfigResponse(AutorepubConfig):
    """Response containing autorepub config."""

    is_active: bool = Field(description="Whether the config is currently active (subscribed and processing)")


class AutorepubConfigListResponse(BaseModel):
    """List of autorepub configs."""

    configs: list[AutorepubConfigResponse] = Field(default_factory=list)
    count: int = Field(description="Number of configs")


@router.post("/configs", response_model=AutorepubConfigResponse)
async def create_config(
    config: AutorepubConfig,
    config_manager: AutorepubConfigManagerDep,
    autorepub_mqtt_manager: AutorepubMQTTManagerDep,
    autorepub_rabbitmq_manager: AutorepubRabbitMQManagerDep,
) -> AutorepubConfigResponse:
    """Create a temporary autorepub config."""

    if not config_manager.is_config_applicable(config):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Config is not applicable to the current instance_id={settings.instance_id}",
        )

    added = config_manager.add_temporary_config(config)
    if not added:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Config {config.name} already exists",
        )
    if config.autostart:
        await config_manager.activate_config(config.name)
        if config.type == AutorepubConfigType.RABBITMQ:
            await autorepub_rabbitmq_manager.subscribe_to_config(config)
        else:
            await autorepub_mqtt_manager.subscribe_to_config(config)

    return AutorepubConfigResponse(
        name=config.name,
        type=config.type,
        source_instance_id=config.source_instance_id,
        target_instances=config.target_instances,
        source_topic=config.source_topic,
        target_topic=config.get_target_topic(),
        queue_name=config.queue_name,
        deduplication=config.deduplication,
        autostart=config.autostart,
        retry_max_attempts=config.retry_max_attempts,
        retry_backoff_base=config.retry_backoff_base,
        retry_multiplier=config.retry_multiplier,
        retry_max_delay=config.retry_max_delay,
        is_active=config_manager.is_config_active(config.name),
    )


@router.delete("/configs")
async def delete_config(
    name: str,
    config_manager: AutorepubConfigManagerDep,
    autorepub_mqtt_manager: AutorepubMQTTManagerDep,
    autorepub_rabbitmq_manager: AutorepubRabbitMQManagerDep,
) -> dict:
    """Delete a temporary autorepub config."""

    config = config_manager.get_temporary_config(name)
    if not config:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Temporary config {name} not found",
        )
    await config_manager.deactivate_config(config.name)
    if config.type == AutorepubConfigType.RABBITMQ:
        await autorepub_rabbitmq_manager.unsubscribe_from_config(config)
    else:
        await autorepub_mqtt_manager.unsubscribe_from_config(config)
    await config_manager.delete_temporary_config(config.name)

    return {"name": config.name, "deleted": True}


@router.get("/configs", response_model=AutorepubConfigListResponse)
async def list_configs(
    config_manager: AutorepubConfigManagerDep,
    only_active: bool = Query(default=False),
) -> AutorepubConfigListResponse:
    """List all autorepub configs (YAML + temporary)."""
    configs = config_manager.get_configs(is_active=(only_active if only_active else None))
    config_responses = [
        AutorepubConfigResponse(
            name=cfg.name,
            type=cfg.type,
            source_instance_id=cfg.source_instance_id,
            target_instances=cfg.target_instances,
            source_topic=cfg.source_topic,
            target_topic=cfg.get_target_topic(),
            queue_name=cfg.queue_name,
            deduplication=cfg.deduplication,
            autostart=cfg.autostart,
            retry_max_attempts=cfg.retry_max_attempts,
            retry_backoff_base=cfg.retry_backoff_base,
            retry_multiplier=cfg.retry_multiplier,
            retry_max_delay=cfg.retry_max_delay,
            is_active=config_manager.is_config_active(cfg.name),
        )
        for cfg in configs
    ]
    return AutorepubConfigListResponse(configs=config_responses, count=len(config_responses))


@router.get("/configs/activate")
@router.post("/configs/activate")
async def activate_config(
    name: str,
    config_manager: AutorepubConfigManagerDep,
    autorepub_mqtt_manager: AutorepubMQTTManagerDep,
    autorepub_rabbitmq_manager: AutorepubRabbitMQManagerDep,
) -> dict:
    """Activate an autorepub config (set Redis key, subscribe to topic)."""

    config = config_manager.get_config(name)
    if not config:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Config {name} not found",
        )
    await config_manager.activate_config(name)
    if config.type == AutorepubConfigType.RABBITMQ:
        await autorepub_rabbitmq_manager.subscribe_to_config(config)
    else:
        await autorepub_mqtt_manager.subscribe_to_config(config)

    return {"name": config.name, "activated": True}


@router.get("/configs/deactivate")
@router.post("/configs/deactivate")
async def deactivate_config(
    name: str,
    config_manager: AutorepubConfigManagerDep,
    autorepub_mqtt_manager: AutorepubMQTTManagerDep,
    autorepub_rabbitmq_manager: AutorepubRabbitMQManagerDep,
) -> dict:
    """Deactivate an autorepub config (delete Redis key, unsubscribe from topic)."""

    config = config_manager.get_config(name)
    if not config:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Config {name} not found",
        )
    await config_manager.deactivate_config(name)
    if config.type == AutorepubConfigType.RABBITMQ:
        await autorepub_rabbitmq_manager.unsubscribe_from_config(config)
    else:
        await autorepub_mqtt_manager.unsubscribe_from_config(config)

    return {"name": config.name, "deactivated": True}

# ─────────────────────────────────────────────────────────────────────────
# Instance suspension endpoints
# ─────────────────────────────────────────────────────────────────────────

def parse_comma_separated_vehicle_ids(
    vehicle_ids: str = Query(
        description="Comma-separated list of vehicle ids (only for server)",
        examples=["4,9,17,22"],
    )
) -> list[int]:
    return [
        int(v_id.strip())
        for v_id in vehicle_ids.split(",")
        if v_id.strip().isdigit()
    ]


class VehicleIDsRequest(BaseModel):
    vehicle_ids: list[int] = Field(
        description="List of vehicle ids (only for server)",
        examples=[[4,9,17,22]],
    )


def vehicle_ids_to_instance_ids(vehicle_ids: list[int]) -> list[str]:
    if vehicle_ids:
        # server branch
        instance_ids = [f"{BORT_INSTANCE_ID_PREFIX}{v_id}" for v_id in vehicle_ids]
    else:
        # bort branch
        instance_ids = [SERVER_INSTANCE_ID]
    return instance_ids


async def suspend_instances(vehicle_ids: list[int]) -> dict:
    config_manager = get_autorepub_config_manager()
    autorepub_mqtt_manager = get_autorepub_mqtt_manager()
    autorepub_rabbitmq_manager = get_autorepub_rabbitmq_manager()

    instance_ids = vehicle_ids_to_instance_ids(vehicle_ids)
    suspended_ids = await config_manager.suspend_instances(instance_ids)
    await autorepub_rabbitmq_manager.suspend_instances(suspended_ids)
    await autorepub_mqtt_manager.suspend_instances(suspended_ids)
    return {"success": True}


async def suspend_instances_bort() -> dict:
    return await suspend_instances([])


async def suspend_instances_server(
    vehicle_ids: list[int] = Depends(parse_comma_separated_vehicle_ids),
) -> dict:
    return await suspend_instances(vehicle_ids)


async def suspend_instances_post_server(data: VehicleIDsRequest) -> dict:
    return await suspend_instances(data.vehicle_ids)


if settings.instance_id == SERVER_INSTANCE_ID:
    router.get("/suspend")(suspend_instances_server)
    router.post("/suspend")(suspend_instances_post_server)
else:
    router.get("/suspend")(suspend_instances_bort)
    router.post("/suspend")(suspend_instances_bort)


async def resume_instances(vehicle_ids: list[int]) -> dict:
    config_manager = get_autorepub_config_manager()
    autorepub_mqtt_manager = get_autorepub_mqtt_manager()
    autorepub_rabbitmq_manager = get_autorepub_rabbitmq_manager()

    instance_ids = vehicle_ids_to_instance_ids(vehicle_ids)
    resumed_ids = await config_manager.resume_instances(instance_ids)
    autorepub_rabbitmq_manager.resume_instances(resumed_ids)
    await autorepub_mqtt_manager.resume_instances(resumed_ids)
    return {"success": True}


async def resume_instances_bort() -> dict:
    return await resume_instances([])


async def resume_instances_server(
    vehicle_ids: list[int] = Depends(parse_comma_separated_vehicle_ids),
) -> dict:
    return await resume_instances(vehicle_ids)


async def resume_instances_post_server(data: VehicleIDsRequest) -> dict:
    return await resume_instances(data.vehicle_ids)


if settings.instance_id == SERVER_INSTANCE_ID:
    router.get("/resume")(resume_instances_server)
    router.post("/resume")(resume_instances_post_server)
else:
    router.get("/resume")(resume_instances_bort)
    router.post("/resume")(resume_instances_bort)
