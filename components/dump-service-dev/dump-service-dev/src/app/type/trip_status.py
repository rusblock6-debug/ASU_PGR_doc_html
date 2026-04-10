# ruff: noqa: D100, D101
from enum import StrEnum


class TripStatus(StrEnum):
    STATE_TRANSITION = "state_transition"
    TRIP_STARTED = "trip_started"
    TRIP_COMPLETED = "trip_completed"

    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value: object) -> "TripStatus":
        """Чтобы не тянуть все статусы, взял 3 для понимания какие они бывают в принципе.

        :param value: Object
        :return: TripStatus
        """
        return cls.UNKNOWN
