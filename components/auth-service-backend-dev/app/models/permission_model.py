from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from .associations import role_permissions
from ..database.base import Base


class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
