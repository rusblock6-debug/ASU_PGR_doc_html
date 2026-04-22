"""API роутеры приложения."""

from . import (
    api,
    enterprise,
    health,
    load_type,
    load_type_category,
    organization_categories,
    shift_service,
    statuses,
    sync,
    vehicle_models,
    vehicles,
    work_regimes,
)

__all__ = [
    "health",
    "api",
    "enterprise",
    "work_regimes",
    "vehicles",
    "vehicle_models",
    "statuses",
    "organization_categories",
    "load_type",
    "load_type_category",
    "shift_service",
    "sync",
]
