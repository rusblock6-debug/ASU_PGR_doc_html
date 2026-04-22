from typing import Any

from starlette import status


class BaseResponseException(Exception):
    """
    Base exception for all response exceptions
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "BAD_REQUEST",
        entity_id: Any = None,
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        self.entity_id = entity_id
