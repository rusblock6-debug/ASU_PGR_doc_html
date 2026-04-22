from sqlalchemy import Column, Integer, ForeignKey, Table, Boolean

from app.database.base import Base

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
    Column("can_view", Boolean, nullable=False, default=False),
    Column("can_edit", Boolean, nullable=False, default=False),
)
