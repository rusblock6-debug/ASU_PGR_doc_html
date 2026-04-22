from enum import StrEnum


class PlaceTypeEnum(StrEnum):
    load = "load"
    unload = "unload"
    reload = "reload"
    transit = "transit"
    park = "park"


class RemainingChangeTypeEnum(StrEnum):
    """Тип изменения остатка на месте"""

    # ВАЖНО: семантика дельты задаётся trip-service:
    # - loading: забрали с места -> delta обычно отрицательная (остаток уменьшается)
    # - unloading: привезли на место -> delta обычно положительная (остаток увеличивается)
    loading = "loading"
    unloading = "unloading"
    initial = "initial"  # Начальный остаток при создании места
