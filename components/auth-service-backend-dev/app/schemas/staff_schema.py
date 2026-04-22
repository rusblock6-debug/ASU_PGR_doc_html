from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from app.schemas.common import PaginationBase


class StaffBase(BaseModel):
    """
    Базовая схема персонала.
    """
    name: str = Field(..., description="Имя сотрудника")
    surname: str = Field(..., description="Фамилия сотрудника")
    patronymic: Optional[str] = Field(default=None, description="Отчество сотрудника")
    birth_date: Optional[date] = Field(default=None, description="Дата рождения сотрудника")
    phone: Optional[str] = Field(default=None, description="Номер телефона сотрудника")
    email: Optional[str] = Field(default=None, description="Почта сотрудника")
    position: Optional[str] = Field(default=None, description="Должность сотрудника")
    department: Optional[str] = Field(default=None, description="Подразделение сотрудника")
    personnel_number: str = Field(..., description="Табельный номер сотрудника")


class StaffUserBase(StaffBase):
    """
    Базовая схема персонала с пользовательскими данными.
    """
    username: str = Field(..., description="Логин сотрудника")
    password: str = Field(..., description="Пароль сотрудника")
    role_id: int = Field(..., description="ID роли сотрудника")
    is_active: bool = Field(default=True, description="Идентификатор активности пользователя")


class StaffCreate(StaffUserBase):
    """
    Схема создания персонала.
    """


class StaffUpdate(BaseModel):
    """
    Схема обновления персонала.
    Все поля optional - передавайте только те, которые нужно изменить.
    """
    name: Optional[str] = Field(default=None , description="Имя сотрудника")
    surname: Optional[str] = Field(default=None, description="Фамилия сотрудника")
    patronymic: Optional[str] = Field(default=None, description="Отчество сотрудника")
    birth_date: Optional[date] = Field(default=None, description="Дата рождения сотрудника")
    phone: Optional[str] = Field(default=None, description="Номер телефона сотрудника")
    email: Optional[str] = Field(default=None, description="Почта сотрудника")
    position: Optional[str] = Field(default=None, description="Должность сотрудника")
    department: Optional[str] = Field(default=None, description="Подразделение сотрудника")
    personnel_number: Optional[str] = Field(default=None, description="Табельный номер сотрудника")
    username: Optional[str] = Field(default=None, description="Логин сотрудника")
    password: Optional[str] = Field(default=None, description="Пароль сотрудника")
    role_id: Optional[int] = Field(default=None, description="ID роли сотрудника")
    is_active: bool = Field(default=True, description="Идентификатор активности пользователя")


class StaffResponse(StaffUserBase):
    staff_id: int = Field(..., description="ID сотрудника")
    user_id: int = Field(..., description="ID привязанного пользователя к сотруднику")
    role_name: str = Field(..., description="Наименование роли сотрудника")
    is_active: bool = Field(..., description="Идентификатор активности пользователя")


class StaffListResponse(PaginationBase[StaffResponse]):
    """
    Ответ списка персонала с пагинацией.
    """
