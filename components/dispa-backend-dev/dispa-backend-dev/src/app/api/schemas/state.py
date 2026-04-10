"""Pydantic схемы для State Machine."""

from pydantic import BaseModel, Field


class StateMachineResponse(BaseModel):
    """Схема ответа текущего состояния State Machine."""

    state: str = Field(..., description="Текущее состояние")
    cycle_id: str | None = Field(None, description="ID активного цикла")
    task_id: str | None = Field(None, description="ID активного задания")
    last_tag_id: int | None = Field(None, description="ID последней метки/точки")
    last_place_id: int | None = Field(None, description="ID последнего места")
    last_transition: str = Field(..., description="Время последнего перехода")
    previous_state: str | None = Field(None, description="Предыдущее состояние перед idle")


class ManualTransitionRequest(BaseModel):
    """Схема запроса ручного перехода состояния."""

    new_state: str = Field(..., description="Новое состояние")
    reason: str | None = Field(None, description="Причина перехода")
    comment: str | None = Field(None, description="Комментарий оператора")
