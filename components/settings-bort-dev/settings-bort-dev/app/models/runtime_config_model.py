from sqlalchemy import Column, Integer, Text

from app.database.base import Base


class RuntimeConfig(Base):
    __tablename__ = "runtime_config"

    id = Column(Integer, primary_key=True, index=True)
    settings_url = Column(Text, nullable=False)
    enterprise_server_url = Column(Text, nullable=False)
