"""Enums перечисление допустимых значений для валидации и документации Swagger."""

from .statuses import AnalyticCategoryEnum
from .vehicles import VehicleStatusEnum, VehicleTypeEnum

__all__ = [
    # Vehicle
    "VehicleTypeEnum",
    "VehicleStatusEnum",
    # Status
    "AnalyticCategoryEnum",
]
