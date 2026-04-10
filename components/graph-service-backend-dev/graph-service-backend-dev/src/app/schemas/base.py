from pydantic import BaseModel as PydanticModel
from pydantic import ConfigDict


class APIBaseModel(PydanticModel):
    model_config = ConfigDict(
        from_attributes=True,
    )
