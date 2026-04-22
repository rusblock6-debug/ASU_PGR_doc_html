"""Enums для транспортных средств."""

from enum import StrEnum


class VehicleTypeEnum(StrEnum):
    """Тип транспортного средства."""

    shas = "shas"
    pdm = "pdm"
    vehicle = "vehicle"


class VehicleStatusEnum(StrEnum):
    """Статус транспортного средства."""

    active = "active"
    maintenance = "maintenance"
    repair = "repair"
    inactive = "inactive"
