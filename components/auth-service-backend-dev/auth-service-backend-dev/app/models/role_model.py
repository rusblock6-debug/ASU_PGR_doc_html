from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from .associations import role_permissions
from ..database.base import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)

    users = relationship("User", back_populates="role")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")

    @property
    def permissions_names(self) -> list[str]:
        return [p.name for p in self.permissions]
