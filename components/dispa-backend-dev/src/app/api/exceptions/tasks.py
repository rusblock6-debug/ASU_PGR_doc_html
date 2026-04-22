"""Исключения API для задач (shift_task, route_task)."""

from starlette import status

from app.api.exceptions.base import BaseResponseException


class ShiftTaskNotFoundException(BaseResponseException):
    """Сменное задание не найдено."""

    def __init__(self, entity_id: str):
        super().__init__(
            message="ShiftTask not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code="SHIFT_TASK_NOT_FOUND",
            entity_id=entity_id,
        )


class PreviousShiftTaskNotFoundException(BaseResponseException):
    """Предыдущее сменное задание не найдено."""

    def __init__(self) -> None:
        super().__init__(
            message="Previous ShiftTask not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code="PREVIOUS_SHIFT_TASK_NOT_FOUND",
        )


class RouteTaskNotFoundException(BaseResponseException):
    """Маршрутное задание не найдено."""

    def __init__(self, entity_id: str):
        super().__init__(
            message="RouteTask not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code="ROUTE_TASK_NOT_FOUND",
            entity_id=entity_id,
        )
