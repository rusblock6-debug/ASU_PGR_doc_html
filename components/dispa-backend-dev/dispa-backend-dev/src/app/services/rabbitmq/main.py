"""Менеджер RabbitMQ соединений и publisher-ов."""

from app.core.config import settings
from app.enums.config import ServiceModeEnum
from app.services.rabbitmq.bort.publisher import VehiclePublisherBortManager
from app.services.rabbitmq.config.logger import get_logger
from app.services.rabbitmq.server.publisher import ServerPublisherBortManager

logger = get_logger()


class RabbitMQManager:
    """Менеджер для выбора и создания RabbitMQ publisher-а в зависимости от режима сервиса."""

    def __init__(self) -> None:
        self.mode = settings.service_mode

    @property
    def publisher_manager(self) -> ServerPublisherBortManager | VehiclePublisherBortManager:
        """Вернуть publisher manager для текущего режима сервиса."""
        match self.mode:
            case ServiceModeEnum.bort:
                logger.info(f"Rabbit handler запущен в режиме: {settings.service_mode}")
                return VehiclePublisherBortManager(vehicle_id=settings.vehicle_id)
            case ServiceModeEnum.server:
                logger.info(f"Rabbit handler запущен в режиме: {settings.service_mode}")
                return ServerPublisherBortManager()
            case _:
                logger.error(f"Unknown service mode: {settings.service_mode}")
                raise RuntimeError(f"Unsupported service_mode: {settings.service_mode}")


rabbitmq_manager = RabbitMQManager()
publisher_manager = rabbitmq_manager.publisher_manager
