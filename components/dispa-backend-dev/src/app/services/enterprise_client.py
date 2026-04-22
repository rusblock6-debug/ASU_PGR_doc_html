"""HTTP клиент для взаимодействия с enterprise-service."""

from datetime import UTC, date, datetime
from typing import Any

import httpx
from loguru import logger

from app.core.config import settings


class EnterpriseServiceClient:
    """Клиент для HTTP-запросов к enterprise-service."""

    def __init__(self) -> None:
        self.base_url = settings.enterprise_service_url
        self.timeout = httpx.Timeout(30.0, connect=10.0)

    async def get_prev_shift(
        self,
        work_regime_id: int,
        current_shift_number: int,
        current_date: date,
    ) -> dict[str, Any] | None:
        """Получить информацию о предыдущей смене из enterprise-service.

        Вызывает GET /shift-service/prev-shift

        Args:
            work_regime_id: ID режима работы
            current_shift_number: Текущий номер смены
            current_date: Текущая дата

        Returns:
            Словарь с информацией о предыдущей смене или None
        """
        url = f"{self.base_url}/api/shift-service/prev-shift"
        params = {
            "work_regime_id": str(work_regime_id),
            "current_shift_number": str(current_shift_number),
            "current_date": current_date.isoformat(),
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)

                if response.status_code == 404:
                    logger.warning(
                        "Previous shift not found",
                        work_regime_id=work_regime_id,
                        current_shift_number=current_shift_number,
                        current_date=current_date.isoformat(),
                    )
                    return None

                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(
                "HTTP error getting prev shift from enterprise-service",
                url=url,
                error=str(e),
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error getting prev shift",
                url=url,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_all_statuses(self) -> list[dict[str, Any]]:
        """Получить список всех статусов из enterprise-service.

        Использует endpoint GET /api/statuses без пагинации (возвращает все записи).

        Returns:
            Список словарей с информацией о статусах:
            [{"id": 1, "system_name": "idle", "is_work_status": false, ...}, ...]
        """
        url = f"{self.base_url}/api/statuses"
        # Без параметров page и size возвращает все записи

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                # Endpoint возвращает: {"total": N, "page": 1, "size": N, "items": [...]}
                items = data.get("items", [])

                logger.info(
                    "Retrieved statuses from enterprise-service",
                    count=len(items),
                    total=data.get("total", 0),
                )
                return items

        except httpx.HTTPError as e:
            logger.error(
                "HTTP error getting statuses",
                url=url,
                error=str(e),
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error getting statuses",
                url=url,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_active_work_regimes(self) -> list[dict[str, Any]]:
        """Получить список всех активных режимов работы из enterprise-service.

        Использует существующий endpoint GET /work-regimes с параметрами:
        - is_active=true (только активные)
        - size=100 (достаточно для всех режимов)
        - page=1

        Returns:
            Список словарей с информацией о режимах работы:
            [{"id": 1, "name": "Основной", "is_active": true, ...}, ...]
        """
        url = f"{self.base_url}/api/work-regimes"
        params = {
            "is_active": "true",
            "size": "100",
            "page": "1",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                # Endpoint возвращает: {"total": N, "page": 1, "size": 100, "items": [...]}
                items = data.get("items", [])

                logger.info(
                    "Retrieved active work regimes from enterprise-service",
                    count=len(items),
                    total=data.get("total", 0),
                )
                return items

        except httpx.HTTPError as e:
            logger.error(
                "HTTP error getting active work regimes",
                url=url,
                params=params,
                error=str(e),
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error getting active work regimes",
                url=url,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_active_vehicles(self, enterprise_id: int = 1) -> list[dict[str, Any]]:
        """Получить список всех активных транспортных средств из enterprise-service.

        Использует endpoint GET /api/vehicles с параметрами:
        - enterprise_id: ID предприятия
        - is_active=true: только активные

        Returns:
            Список словарей с информацией о транспортных средствах
        """
        url = f"{self.base_url}/api/vehicles"
        params = {
            "enterprise_id": str(enterprise_id),
            "is_active": "true",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                # Endpoint возвращает: {"total": N, "page": 1, "size": N, "items": [...]}
                items = data.get("items", [])

                logger.info(
                    "Retrieved active vehicles from enterprise-service",
                    count=len(items),
                    total=data.get("total", 0),
                )
                return items

        except httpx.HTTPError as e:
            logger.error(
                "HTTP error getting active vehicles",
                url=url,
                params=params,
                error=str(e),
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error getting active vehicles",
                url=url,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_vehicle_by_id(self, vehicle_id: int) -> dict[str, Any] | None:
        """Получить технику по ID (GET /api/vehicles/{vehicle_id}), с вложенной model."""
        url = f"{self.base_url}/api/vehicles/{vehicle_id}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, dict) else None
        except httpx.HTTPError as e:
            logger.debug(
                "HTTP error getting vehicle by id from enterprise-service",
                url=url,
                vehicle_id=vehicle_id,
                error=str(e),
            )
            return None
        except Exception as e:
            logger.debug(
                "Unexpected error getting vehicle by id",
                url=url,
                vehicle_id=vehicle_id,
                error=str(e),
            )
            return None

    async def get_shift_time_range(
        self,
        shift_date: date,
        shift_number: int,
        work_regime_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Получить временной диапазон для конкретной смены.

        Вызывает GET /api/shift-service/get-shift-time-range

        Args:
            shift_date: Дата смены
            shift_number: Номер смены (1, 2, etc.)
            work_regime_id: ID режима работы (опционально)

        Returns:
            Словарь с 'start_time' и 'end_time' или None если смена не найдена
        """
        url = f"{self.base_url}/api/shift-service/get-shift-time-range"
        params: dict[str, str] = {
            "shift_date": shift_date.isoformat(),
            "shift_number": str(shift_number),
        }
        if work_regime_id is not None:
            params["work_regime_id"] = str(work_regime_id)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)

                if response.status_code == 404:
                    logger.warning(
                        "Shift time range not found",
                        shift_date=shift_date.isoformat(),
                        shift_number=shift_number,
                        work_regime_id=work_regime_id,
                    )
                    return None

                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(
                "HTTP error getting shift time range from enterprise-service",
                url=url,
                error=str(e),
                exc_info=True,
            )
            return None
        except Exception as e:
            logger.error(
                "Unexpected error getting shift time range",
                url=url,
                error=str(e),
                exc_info=True,
            )
            return None

    async def get_current_shift_info(
        self,
        work_regime_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Получить информацию о текущей смене (shift_date и shift_num).

        Вызывает GET /api/shift-service/get-shift-info-by-timestamp с текущим временем.

        Args:
            work_regime_id: ID режима работы (опционально, если None - берется первый активный)

        Returns:
            Словарь с 'shift_date' (str) и 'shift_num' (int) или None если не найдено
        """
        return await self.get_shift_info_by_timestamp(
            timestamp=datetime.now(UTC),
            work_regime_id=work_regime_id,
        )

    async def get_shift_info_by_timestamp(
        self,
        timestamp: datetime,
        work_regime_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Получить информацию о смене (shift_date и shift_num) для конкретного timestamp.

        Вызывает GET /api/shift-service/get-shift-info-by-timestamp.

        Args:
            timestamp: Время для определения смены
            work_regime_id: ID режима работы (опционально, если None - берется первый активный)

        Returns:
            Словарь с 'shift_date' (str) и 'shift_num' (int) или None если не найдено
        """
        url = f"{self.base_url}/api/shift-service/get-shift-info-by-timestamp"
        # Если timestamp naive - считаем UTC, иначе оставляем as is
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)

        params: dict[str, str] = {
            "timestamp": timestamp.isoformat(),
        }
        if work_regime_id is not None:
            params["work_regime_id"] = str(work_regime_id)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)

                if response.status_code == 404:
                    logger.warning(
                        "Shift info not found for timestamp",
                        timestamp=timestamp.isoformat(),
                        work_regime_id=work_regime_id,
                    )
                    return None

                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(
                "HTTP error getting shift info by timestamp from enterprise-service",
                url=url,
                timestamp=timestamp.isoformat(),
                error=str(e),
                exc_info=True,
            )
            return None
        except Exception as e:
            logger.error(
                "Unexpected error getting shift info by timestamp",
                url=url,
                timestamp=timestamp.isoformat(),
                error=str(e),
                exc_info=True,
            )
            return None

    async def get_shift_info_and_time_range(
        self,
        timestamp: datetime,
        work_regime_id: int | None = None,
    ) -> dict[str, int | date | datetime] | None:
        """Получить дату, номер и временной диапазон смены по конкретному timestamp.

        Вызывает методы:
            get_shift_info_by_timestamp()
            get_shift_time_range()

        Args:
            timestamp: Время для определения смены
            work_regime_id: ID режима работы (None - берется первый активный)

        Returns:
            dict: Словарь с данными смены или None:
                shift_date (date)
                shift_num (int)
                start_time (datetime)
                end_time (datetime)
        """
        shift_info = await self.get_shift_info_by_timestamp(timestamp, work_regime_id)
        if not shift_info:
            return None

        try:
            shift_date = date.fromisoformat(shift_info["shift_date"])
            shift_num = shift_info["shift_num"]
        except (ValueError, TypeError, KeyError):
            logger.error(
                "Unexpected format of shift info returned from enterprise-service",
                timestamp=timestamp.isoformat(),
                work_regime_id=work_regime_id,
                shift_info=shift_info,
            )
            return None

        shift_time_range = await self.get_shift_time_range(shift_date, shift_num, work_regime_id)
        if not shift_time_range:
            return None

        try:
            start_time = datetime.fromisoformat(shift_time_range["start_time"])
            end_time = datetime.fromisoformat(shift_time_range["end_time"])
        except (ValueError, TypeError, KeyError):
            logger.error(
                "Unexpected format of shift time range returned from enterprise-service",
                timestamp=timestamp.isoformat(),
                work_regime_id=work_regime_id,
                shift_date=shift_date,
                shift_num=shift_num,
                shift_time_range=shift_time_range,
            )
            return None
        return {
            "shift_date": shift_date,
            "shift_num": shift_num,
            "start_time": start_time,
            "end_time": end_time,
        }


# Глобальный экземпляр клиента
enterprise_client = EnterpriseServiceClient()
