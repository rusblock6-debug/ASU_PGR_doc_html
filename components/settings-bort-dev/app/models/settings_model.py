from sqlalchemy import Column, Integer, JSON
from app.database.base import Base


class Settings(Base):
    __tablename__ = "secrets"

    id = Column(Integer, primary_key=True, index=True)
    secrets = Column(JSON, nullable=False)
