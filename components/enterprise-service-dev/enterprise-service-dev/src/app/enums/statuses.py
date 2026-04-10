"""Enum для статусов."""

from enum import StrEnum


class AnalyticCategoryEnum(StrEnum):
    """Аналитическая категория статуса.

    Отображение для пользователя:
    - productive: Производственная (продуктивное время)
    - non_productive: Не продуктивное время
    - work_delays: Рабочие задержки
    - external_causes: Простои по внешним причинам
    - planned_maintenance: Ремонт плановый
    - unplanned_maintenance: Ремонт не плановый
    - unscheduled_time: Не запланированное время
    """

    productive = "productive"
    non_productive = "non_productive"
    work_delays = "work_delays"
    external_causes = "external_causes"
    planned_maintenance = "planned_maintenance"
    unplanned_maintenance = "unplanned_maintenance"
    unscheduled_time = "unscheduled_time"

    @classmethod
    def get_display_name(cls, value: str) -> str:
        """Получить отображаемое имя на русском."""
        display_names: dict[str, str] = {
            cls.productive: "Производственная (продуктивное время)",
            cls.non_productive: "Не продуктивное время",
            cls.work_delays: "Рабочие задержки",
            cls.external_causes: "Простои по внешним причинам",
            cls.planned_maintenance: "Ремонт плановый",
            cls.unplanned_maintenance: "Ремонт не плановый",
            cls.unscheduled_time: "Не запланированное время",
        }
        return display_names.get(value, value)
