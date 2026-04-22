from pydantic import BaseModel
from typing import Optional

class PermissionBase(BaseModel):
    name: str
    description: Optional[str] = None

class PermissionCreate(PermissionBase):
    pass

class PermissionOut(PermissionBase):
    id: int

    class Config:
        from_attributes = True

class PermissionCheck(BaseModel):
    permission: str