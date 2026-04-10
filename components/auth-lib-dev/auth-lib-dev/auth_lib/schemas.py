from pydantic import BaseModel


class PermissionSchema(BaseModel):
    id: int
    name: str
    can_view: bool
    can_edit: bool


class RoleSchema(BaseModel):
    id: int
    name: str
    permissions: list[PermissionSchema]


class UserPayload(BaseModel):
    id: int
    username: str
    role: RoleSchema
    exp: int
