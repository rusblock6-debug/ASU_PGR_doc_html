"""API endpoints для управления техникой (fleet-control).

Новый неймспейс вместо route-summary. Старые роуты оставлены как алиасы.
"""

import asyncio

from auth_lib.dependencies import require_permission
from auth_lib.permissions import Action, Permission
from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.route_summary import (
    DispatcherAssignmentCreateRequest,
    DispatcherAssignmentDecisionRequest,
    DispatcherAssignmentResponse,
    FleetControlResponse,
    FleetControlRouteItem,
    RouteTemplateCreateRequest,
    RouteTemplateResponse,
    RouteTemplateUpdateRequest,
)
from app.api.schemas.shift_load_type_volumes import ShiftLoadTypeVolumesResponse
from app.api.schemas.vehicle_tooltip import VehicleTooltipResponse
from app.core.config import settings
from app.database.models import DispatcherAssignment
from app.database.session import AsyncSessionLocal, get_db_session
from app.enums.config import ServiceModeEnum
from app.enums.dispatcher_assignments import DispatcherAssignmentStatusEnum
from app.services.rabbitmq.config.enum import MessageEventEnum, MessageTypeEnum
from app.services.rabbitmq.main import publisher_manager
from app.services.rabbitmq.schemas.base import BaseMsgScheme, MessageData
from app.services.route_summary import (
    create_empty_route_template,
    create_or_update_dispatcher_assignment,
    decide_dispatcher_assignment,
    delete_route_template_and_cancel_tasks,
    get_fleet_control,
    get_route_summary,
    update_route_places,
)
from app.services.shift_load_type_volumes import get_shift_load_type_volumes
from app.services.vehicle_tooltip import get_vehicle_tooltip
from app.utils.session import SessionDepends

router = APIRouter(prefix="/fleet-control", tags=["fleet-control"])


async def _auto_approve_assignment_later(assignment_id: int, delay_seconds: int) -> None:
    """Автопринять pending-назначение через заданную задержку."""
    if delay_seconds <= 0:
        return
    try:
        await asyncio.sleep(delay_seconds)
        async with AsyncSessionLocal() as db:
            assignment = await db.get(DispatcherAssignment, assignment_id)
            if assignment is None:
                return
            if assignment.status != DispatcherAssignmentStatusEnum.PENDING.value:
                return
            await decide_dispatcher_assignment(assignment_id=assignment_id, approved=True, db=db)
    except Exception as e:
        logger.exception(
            "Auto-approve dispatcher assignment failed",
            assignment_id=assignment_id,
            delay_seconds=delay_seconds,
            error=str(e),
        )


@router.get(
    "",
    response_model=FleetControlResponse,
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.VIEW)))],
)
async def fleet_control(
    session: SessionDepends,
    route_id: list[str] | None = Query(
        default=None,
        description="Список route_id (place_a_id-place_b_id), по которым нужно отфильтровать routes на странице",
    ),
) -> FleetControlResponse:
    """Единый ответ для страницы Fleet Control."""
    result = await get_fleet_control(session)
    if route_id:
        wanted = set(route_id)
        result.routes = [r for r in result.routes if r.route_id in wanted]
    return result


@router.get(
    "/routes",
    response_model=list[FleetControlRouteItem],
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.VIEW)))],
)
async def fleet_control_routes(session: SessionDepends) -> list[FleetControlRouteItem]:
    """Список всех маршрутов текущей смены (как на странице fleet-control)."""
    summary = await get_route_summary(session)
    if summary.shift_date is None or summary.shift_num is None:
        return []

    return [
        FleetControlRouteItem(
            route_id=f"{r.place_a_id}-{r.place_b_id}",
            place_a_id=r.place_a_id,
            place_b_id=r.place_b_id,
        )
        for r in summary.routes
    ]


@router.get(
    "/shift-load-type-volumes",
    response_model=ShiftLoadTypeVolumesResponse,
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.VIEW)))],
)
async def shift_load_type_volumes(
    session: SessionDepends,
    section_id: list[int] | None = Query(
        default=None,
        description="Один или несколько участков",
    ),
    place_id: list[int] | None = Query(
        default=None,
        description="Одно или несколько мест разгрузки",
    ),
) -> ShiftLoadTypeVolumesResponse:
    """Итоги по видам груза за текущую смену (объём из place_remaining_history, тип — с места погрузки)."""
    return await get_shift_load_type_volumes(
        db=session,
        section_ids=tuple(section_id) if section_id else None,
        place_ids=tuple(place_id) if place_id else None,
    )


@router.post(
    "/assignments",
    response_model=DispatcherAssignmentResponse,
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.EDIT)))],
)
async def create_assignment(
    body: DispatcherAssignmentCreateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> DispatcherAssignmentResponse:
    """Создать/обновить назначение техники диспетчером."""
    try:
        result = await create_or_update_dispatcher_assignment(body=body, db=db)
        delay_seconds = settings.auto_approve_dispatcher_assignment_delay_seconds
        if (
            settings.service_mode == ServiceModeEnum.server
            and delay_seconds > 0
            and result.id > 0
            and result.status == DispatcherAssignmentStatusEnum.PENDING.value
        ):
            asyncio.create_task(_auto_approve_assignment_later(result.id, delay_seconds))
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/assignments/{assignment_id}/decision",
    response_model=DispatcherAssignmentResponse,
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.EDIT)))],
)
async def assignment_decision(
    assignment_id: int,
    body: DispatcherAssignmentDecisionRequest,
    db: AsyncSession = Depends(get_db_session),
) -> DispatcherAssignmentResponse:
    """Принять решение диспетчера по назначению (approve/reject)."""
    if settings.service_mode == ServiceModeEnum.bort:
        msg = BaseMsgScheme(
            payload={
                "approved": body.approved,
                "assignment_id": assignment_id,
            },
            message_data=MessageData(
                message_event=MessageEventEnum.update,
                message_type=MessageTypeEnum.dispatcher_assignments,
            ),
        )
        if publisher_manager is None:
            raise RuntimeError("publisher_manager is not initialized")
        await publisher_manager.task_publish(msg, int(settings.vehicle_id))
    try:
        result = await decide_dispatcher_assignment(
            assignment_id=assignment_id,
            approved=body.approved,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Назначение не найдено")
    return result


@router.post(
    "/routes",
    response_model=RouteTemplateResponse,
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.EDIT)))],
)
async def create_route_template(
    body: RouteTemplateCreateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> RouteTemplateResponse:
    """Создать шаблон маршрута (route template) по паре мест."""
    result = await create_empty_route_template(body=body, db=db)
    if not result.success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)
    return result


@router.post(
    "/routes/update-places",
    response_model=RouteTemplateResponse,
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.EDIT)))],
)
async def update_route_template_places(
    body: RouteTemplateUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> RouteTemplateResponse:
    """Обновить состав мест внутри существующего route template."""
    return await update_route_places(body=body, db=db)


@router.delete(
    "/routes/{route_id}",
    response_model=RouteTemplateResponse,
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.EDIT)))],
)
async def delete_route_template(
    route_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> RouteTemplateResponse:
    """Удалить маршрут и отменить связанные route_tasks (по текущей смене)."""
    result = await delete_route_template_and_cancel_tasks(route_id=route_id, db=db)
    if not result.success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)
    return result


@router.get(
    "/vehicles/{vehicle_id}/tooltip",
    response_model=VehicleTooltipResponse,
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.VIEW)))],
)
async def get_vehicle_tooltip_endpoint(
    vehicle_id: int,
    session: SessionDepends,
) -> VehicleTooltipResponse:
    """Данные для тултипа техники."""
    return await get_vehicle_tooltip(vehicle_id=vehicle_id, db=session)
