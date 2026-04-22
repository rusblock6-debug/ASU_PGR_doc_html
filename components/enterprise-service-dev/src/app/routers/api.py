"""Main API router для enterprise-service."""

from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/")
async def api_root() -> dict[str, Any]:
    """Корневой endpoint API."""
    return {
        "service": "enterprise-service",
        "version": "1.0.0",
        "endpoints": {
            "work_regimes": "/api/work-regimes",
            "vehicles": "/api/vehicles",
            "statuses": "/api/statuses",
            "organization_categories": "/api/organization-categories",
            "load_types": "/api/load_types",
            "load_type_categories": "/api/load_type_categories",
        },
    }
