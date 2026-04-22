"""Бизнес-логика приложения в виде сервисов."""

from .api_client import api_client
from .event_publisher import EventPublisher
from .organization_categories import OrganizationCategoryService
from .shift_service import ShiftService
from .statuses import StatusService
from .sync_service import SyncService
from .vehicle_models import VehicleModelService
from .vehicles import VehicleService

__all__ = [
    "ShiftService",
    "SyncService",
    "EventPublisher",
    "VehicleService",
    "VehicleModelService",
    "StatusService",
    "OrganizationCategoryService",
    "api_client",
]
