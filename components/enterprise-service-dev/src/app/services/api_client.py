"""API клиент для внешних сервисов."""

from typing import Any

import httpx
from loguru import logger

from app.core.config import settings
from app.core.logging_config import get_logger, setup_logging

setup_logging()
logger = get_logger(logger, "Api Client")  # type: ignore[arg-type, assignment]


# TODO возможно данный функционал будет заменен
class ApiClient:
    """Клиент для взаимодействия с внешними API."""

    def __init__(self) -> None:
        """Инициализация API клиента."""
        self.headers = {
            "",
        }

    async def get_place(self, place_id: int) -> dict[str, Any]:
        """Получить данные места по ID."""
        try:
            url = (
                f"{settings.api_client.base_graph_service_url}{settings.api_client.place}{place_id}"
            )
            async with httpx.AsyncClient() as client:
                logger.info("Get request", url=url)
                response = await client.get(url)
                response_data = response.json()

                if 400 <= response.status_code < 500:
                    raise ValueError(
                        f"Error get data, status_code: {response.status_code},"
                        f" info: {response_data!s}",
                    )

                return response_data

        except Exception as exc:
            logger.exception("Error in get place request", exc=exc)
            raise exc

    async def update_place_cargo_type(
        self,
        place_id: int,
        cargo_type: int,
    ) -> dict[str, Any] | None:
        """Обновить тип груза для места.

        При использовании данного метода нужно смотреть на модель Place
        и на тело запроса для обновления модели.
        """
        try:
            url = (
                f"{settings.api_client.base_graph_service_url}{settings.api_client.place}{place_id}"
            )
            data = dict()
            data["cargo_type"] = cargo_type
            async with httpx.AsyncClient() as client:
                logger.info("Patch request", url=url)
                response = await client.patch(url, json=data)
                response_data = response.json()

                if 400 <= response.status_code < 500:
                    raise ValueError(
                        f"Error update data, status_code: {response.status_code},"
                        f" info: {response_data!s}",
                    )

                return response_data

        except Exception as exc:
            logger.exception("Error in get place request", exc=exc)
            return None


api_client: ApiClient = ApiClient()
