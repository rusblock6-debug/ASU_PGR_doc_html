"""Pydantic schemas для валидации и сериализации данных."""

from .common import (
    ErrorResponse,
    PaginationBase,
    TimestampBase,
)
from .enterprise import (
    EnterpriseSettingsBase,
    EnterpriseSettingsCreate,
    EnterpriseSettingsResponse,
    EnterpriseSettingsUpdate,
)
from .statuses import (
    OrganizationCategoryBase,
    OrganizationCategoryCreate,
    OrganizationCategoryListResponse,
    OrganizationCategoryResponse,
    OrganizationCategoryUpdate,
    StatusBase,
    StatusCreate,
    StatusListResponse,
    StatusResponse,
    StatusUpdate,
)
from .vehicle_models import (
    VehicleModelBase,
    VehicleModelCreate,
    VehicleModelListResponse,
    VehicleModelResponse,
    VehicleModelUpdate,
)
from .vehicles import (
    VehicleBase,
    VehicleCreate,
    VehicleListResponse,
    VehicleResponse,
    VehicleUpdate,
)
from .work_regimes import (
    ShiftDefinition,
    WorkRegimeBase,
    WorkRegimeCreate,
    WorkRegimeListResponse,
    WorkRegimeResponse,
    WorkRegimeUpdate,
)

__all__ = [
    # Enterprise
    "EnterpriseSettingsBase",
    "EnterpriseSettingsCreate",
    "EnterpriseSettingsUpdate",
    "EnterpriseSettingsResponse",
    # WorkRegimes
    "ShiftDefinition",
    "WorkRegimeBase",
    "WorkRegimeCreate",
    "WorkRegimeUpdate",
    "WorkRegimeResponse",
    "WorkRegimeListResponse",
    # Vehicles
    "VehicleBase",
    "VehicleCreate",
    "VehicleUpdate",
    "VehicleResponse",
    "VehicleListResponse",
    # VehicleModels
    "VehicleModelBase",
    "VehicleModelCreate",
    "VehicleModelUpdate",
    "VehicleModelResponse",
    "VehicleModelListResponse",
    # Statuses
    "StatusBase",
    "StatusCreate",
    "StatusUpdate",
    "StatusResponse",
    "StatusListResponse",
    # OrganizationCategory
    "OrganizationCategoryBase",
    "OrganizationCategoryCreate",
    "OrganizationCategoryUpdate",
    "OrganizationCategoryResponse",
    "OrganizationCategoryListResponse",
    # Common
    "PaginationBase",
    "ErrorResponse",
    "TimestampBase",
]
