from starlette import status

from app.api.exceptions.base import BaseResponseException


class RoleWithNameExists(BaseResponseException):
    def __init__(self, entity_id: int, name: str) -> None:
        super().__init__(
            entity_id = entity_id,
            message = f'Роль с именем {name} существует!',
            status_code = status.HTTP_400_BAD_REQUEST,
            code = "ROLE_WITH_NAME_EXISTS"
        )
