"""Фабрика сервисов для dependency injection в роутерах."""

from app.services.history_service import HistoryService
from app.utils.session import SessionDepends


class Factory:
    """Собирает сервисы с внедрёнными зависимостями."""

    @classmethod
    def get_history_service(
        cls,
        db_session: SessionDepends,
    ) -> HistoryService:
        """Создать `HistoryService` c подключённой сессией БД."""
        return HistoryService(
            db_session=db_session,
        )
