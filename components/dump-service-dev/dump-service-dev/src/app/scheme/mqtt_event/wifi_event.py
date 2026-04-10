# ruff: noqa: D100, D101
from pydantic import BaseModel

from src.app.type import WifiStatus


class WifiEvent(BaseModel):
    status: WifiStatus
