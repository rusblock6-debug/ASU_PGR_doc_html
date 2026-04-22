from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database.base import Base


class Staff(Base):
    __tablename__ = "staff"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    patronymic = Column(String, nullable=True)
    birth_date = Column(DateTime)
    phone = Column(String, nullable=True, unique=True)
    email = Column(String)
    position = Column(String)
    department = Column(String)
    personnel_number = Column(String, nullable=False, unique=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="staff")
