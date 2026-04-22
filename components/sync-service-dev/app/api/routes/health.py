from fastapi import APIRouter

from app.dependencies import AutorepubMQTTClientDep, AutorepubRabbitMQManagerDep, MQTTClientDep, RedisClientDep
from app.settings import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Liveness probe."""
    return {
        "status": "ok",
        "instance_id": settings.instance_id,
        "mode": settings.mode,
    }


@router.get("/ready")
async def readiness_check(
    redis_client: RedisClientDep,
    mqtt_client: MQTTClientDep,
    autorepub_mqtt_client: AutorepubMQTTClientDep,
    autorepub_rabbitmq_manager: AutorepubRabbitMQManagerDep,
) -> dict:
    """Readiness probe."""

    redis_ready = False
    try:
        await redis_client.ping()
        redis_ready = True
    except Exception:
        redis_ready = False

    mqtt_ready = await mqtt_client.is_healthy()
    autorepub_mqtt_ready = await autorepub_mqtt_client.is_healthy()
    autorepub_rabbitmq_ready = (
        autorepub_rabbitmq_manager.connection
        and autorepub_rabbitmq_manager.connection.connected.is_set()
        and autorepub_rabbitmq_manager._channel_dst
        and not autorepub_rabbitmq_manager._channel_dst.pika_obj.is_closed
    )

    is_ready = redis_ready and mqtt_ready and autorepub_mqtt_ready and autorepub_rabbitmq_ready

    return {
        "status": "ready" if is_ready else "not_ready",
        "instance_id": settings.instance_id,
        "hostname": settings.hostname,
        "redis_connected": redis_ready,
        "mqtt_connected": mqtt_ready,
        "autorepub_mqtt_connected": autorepub_mqtt_ready,
        "autorepub_rabbitmq_connected": autorepub_rabbitmq_ready,
        "log_level": settings.log_level,
        "debug_mode": settings.debug_mode,
        "mode": settings.mode,
        "multi_replica_mode": settings.multi_replica_mode,
    }
