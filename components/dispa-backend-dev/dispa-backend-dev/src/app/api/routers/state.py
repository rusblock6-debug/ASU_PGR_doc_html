"""API endpoints для State Machine."""

from typing import Any

from auth_lib.dependencies import require_permission
from auth_lib.permissions import Action, Permission
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.api.schemas.common import MessageResponse
from app.api.schemas.state import ManualTransitionRequest, StateMachineResponse
from app.core.config import settings
from app.services.state_machine import State, get_state_machine
from app.utils.session import SessionDepends

router = APIRouter(prefix="/state", tags=["state-machine"])


@router.get(
    "",
    response_model=StateMachineResponse,
    dependencies=[Depends(require_permission((Permission.WORK_TIME_MAP, Action.VIEW)))],
)
async def get_current_state() -> Any:
    """Получить текущее состояние State Machine для vehicle.

    Возвращает:
    - Текущее состояние
    - ID активного рейса (если есть)
    - ID активного задания (если есть)
    - Последнюю метку и точку
    - Время последнего перехода
    """
    try:
        state_machine = get_state_machine(int(settings.vehicle_id))

        state_data = await state_machine.get_current_state()

        return StateMachineResponse(**state_data)

    except Exception as e:
        logger.error("Get current state error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get("/clear/{vechicle_id}", dependencies=[Depends(require_permission((Permission.WORK_TIME_MAP, Action.EDIT)))])
async def clear_state(vechicle_id: int) -> None:
    """Сбросить состояние State Machine."""
    state_machine = get_state_machine(int(settings.vehicle_id))
    await state_machine.reset_state()


@router.post(
    "/transition",
    response_model=MessageResponse,
    dependencies=[Depends(require_permission((Permission.WORK_TIME_MAP, Action.EDIT)))],
)
async def manual_transition(
    transition_request: ManualTransitionRequest,
    session: SessionDepends,
) -> Any:
    """Ручной переход в новое состояние.

    Используется для отладки и ручного управления State Machine.

    ВНИМАНИЕ: Используйте с осторожностью, может нарушить логику рейсов!
    """
    try:
        # Валидация нового состояния
        try:
            new_state = State(transition_request.new_state)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Некорректное состояние: {transition_request.new_state}",
            ) from None

        vehicle_id = int(settings.vehicle_id)
        state_machine = get_state_machine(vehicle_id)

        logger.warning(
            "Manual state transition requested",
            vehicle_id=vehicle_id,
            new_state=new_state.value,
            reason=transition_request.reason,
        )

        # Выполнить ручной переход
        result = await state_machine.manual_transition(
            new_state=new_state,
            reason=transition_request.reason or "manual",
            comment=transition_request.comment or "",
            db=session,
        )

        return MessageResponse(
            message=f"Переход выполнен: {result['old_state']} → {result['new_state']}",
            success=True,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Manual transition error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка ручного перехода: {str(e)}",
        ) from e


@router.get(
    "/available-states",
    response_model=dict[str, Any],
    dependencies=[Depends(require_permission((Permission.WORK_TIME_MAP, Action.VIEW)))],
)
async def get_available_states() -> dict[str, Any]:
    """Получить список доступных состояний State Machine.

    Возвращает описание каждого состояния.
    """
    return {
        "states": [
            {
                "value": State.IDLE.value,
                "name": "Ожидание задания",
                "description": "Транспорт ожидает назначения задания или начала рейса",
            },
            {
                "value": State.MOVING_EMPTY.value,
                "name": "Движение порожним",
                "description": "Транспорт движется к точке погрузки без груза",
            },
            {
                "value": State.STOPPED_EMPTY.value,
                "name": "Остановка порожним",
                "description": "Транспорт остановлен без груза",
            },
            {
                "value": State.LOADING.value,
                "name": "Погрузка",
                "description": "Происходит погрузка транспорта",
            },
            {
                "value": State.MOVING_LOADED.value,
                "name": "Движение с грузом",
                "description": "Транспорт движется к точке разгрузки с грузом",
            },
            {
                "value": State.STOPPED_LOADED.value,
                "name": "Остановка с грузом",
                "description": "Транспорт остановлен с грузом",
            },
            {
                "value": State.UNLOADING.value,
                "name": "Разгрузка",
                "description": "Происходит разгрузка транспорта",
            },
        ],
    }
