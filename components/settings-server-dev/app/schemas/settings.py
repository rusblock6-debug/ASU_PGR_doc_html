from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class VariableCreateRequest(BaseModel):
    variables: Dict[str, Any]
