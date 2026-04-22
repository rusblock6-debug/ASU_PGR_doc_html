from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.dependencies import OwnershipCoordinatorDep
from app.models.consts import BORT_INSTANCE_ID_PREFIX
from app.settings import settings

router = APIRouter(prefix="/coordination", tags=["coordination"])


class DistributionStatsResponse(BaseModel):
    """Response for distribution stats."""

    known_replicas: int
    known_instances: int
    fair_share: int
    owned_instances: int
    others_instances: int

    claimed: int
    released: int
    failed_claims: int
    expired_claims: int
    stolen_by_others: int


class VehicleIDsDistributionResponse(BaseModel):
    """Response for full distribution."""

    distribution: dict[str | None, list[int]]


@router.get("/stats", response_model=DistributionStatsResponse)
async def get_distribution_stats(
    coordinator: OwnershipCoordinatorDep,
) -> DistributionStatsResponse:
    """Get current distribution statistics for this replica."""

    if not settings.multi_replica_mode:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Multi-replica mode is not enabled")

    stats = coordinator.get_distribution_stats()
    return DistributionStatsResponse(**stats)


@router.get("/distribution", response_model=VehicleIDsDistributionResponse)
async def get_distribution(coordinator: OwnershipCoordinatorDep) -> VehicleIDsDistributionResponse:
    """Get full distribution of instances across all replicas."""

    if not settings.multi_replica_mode:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Multi-replica mode is not enabled")

    distribution = await coordinator.get_full_distribution()

    distribution_v_ids: dict[str | None, list[int]] = {}
    for replica_id, inst_id_list in distribution.items():
        distribution_v_ids[replica_id] = []
        for inst_id in inst_id_list:
            v_id = inst_id.replace(BORT_INSTANCE_ID_PREFIX, "")
            if v_id.isdigit():
                distribution_v_ids[replica_id].append(int(v_id))
        distribution_v_ids[replica_id].sort()
    return VehicleIDsDistributionResponse(distribution=distribution_v_ids)


@router.get("/instances")
async def update_instances(
    coordinator: OwnershipCoordinatorDep,
    instances: list[str] = Query(default=[], alias="i"),
) -> dict:
    """Update the set of instances to coordinate."""

    if not settings.multi_replica_mode:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Multi-replica mode is not enabled")

    await coordinator.update_instances(instances)
    return {"success": True}
