from pydantic import BaseModel
from typing import List, Optional
from .role_schema import RoleBaseId

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class UserOut(BaseModel):
    id: int
    username: str
    is_active: bool
    role: Optional[RoleBaseId] = None

    class Config:
        from_attributes = True

