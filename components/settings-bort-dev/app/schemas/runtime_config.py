from pydantic import BaseModel, Field


class RuntimeConfigPayload(BaseModel):
    settings_url: str = Field(..., min_length=1)
    enterprise_server_url: str = Field(..., min_length=1)
