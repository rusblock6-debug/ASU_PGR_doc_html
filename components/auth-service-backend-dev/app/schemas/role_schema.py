from pydantic import BaseModel, Field
from typing import List, Optional

from app.schemas.common import PaginationBase


class PermissionCreate(BaseModel):
    """
    Схема для создания/обновления разрешения
    """
    name: str = Field(..., description="Название формы для роли")
    can_view: bool = Field(..., description="Разрешение на чтение")
    can_edit: bool = Field(..., description="Разрешение на редактирование")


class RoleCreate(BaseModel):
    """
    Схема для создания новой роли
    """
    name: str = Field(..., description="Название роли")
    description: Optional[str] = Field(default=None, description="Описание роли")
    permissions: List[PermissionCreate]


class RoleResponse(BaseModel):
    """
    Схема ответа с ролью и ее разрешениями
    """
    id: int = Field(..., description="ID роли")
    name: str = Field(..., description="Название роли")
    description: Optional[str] = Field(default=None, description="Описание роли")
    permissions: List[PermissionCreate]

    class Config:
        from_attributes = True


class RoleListResponse(PaginationBase[RoleResponse]):
    """
    Ответ списка ролей с пагинацией.
    """


class RoleUpdate(BaseModel):
    """
    Схема обновления роли.
    Все поля optional - передавайте только те, которые нужно изменить.
    """
    name: Optional[str] = Field(default=None, description="Название роли")
    description: Optional[str] = Field(default=None, description="Описание роли")
    permissions: Optional[List[PermissionCreate]] = Field(default=None, description="Список разрешений для роли")



class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleBaseId(RoleBase):
    id: int

class RoleOut(RoleBase):
    id: int
    permissions_names: List[str] = []

    class Config:
        from_attributes = True
