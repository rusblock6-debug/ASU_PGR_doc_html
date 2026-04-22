"""Default serializer for common Python types."""

from __future__ import annotations

import base64
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID


def default_serializer(val: Any) -> Any:
    """Serialize a value to a JSON-compatible type.

    Handles standard Python types that are not natively JSON-serializable:

    - ``datetime``, ``date``, ``time`` → ISO 8601 string (``isoformat()``)
    - ``UUID`` → string
    - ``Decimal`` → string
    - ``Enum`` → ``.value``
    - ``set``, ``frozenset`` → ``list``
    - ``bytes`` → base64-encoded string
    - pydantic v2 models → ``model_dump(mode="json")`` (duck-typed)
    - unknown types → returned as-is
    """
    # datetime MUST be checked before date (datetime is a subclass of date)
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, time):
        return val.isoformat()
    if isinstance(val, UUID):
        return str(val)
    if isinstance(val, Decimal):
        return str(val)
    if isinstance(val, Enum):
        return val.value
    if isinstance(val, (set, frozenset)):
        return list(val)
    if isinstance(val, bytes):
        return base64.b64encode(val).decode("ascii")
    # pydantic v2 duck-typing (no hard dependency on pydantic)
    if hasattr(val, "model_dump"):
        return val.model_dump(mode="json")
    return val
