"""Перечисления типов изменений остатков."""

from enum import StrEnum


class RemainingChangeTypeEnum(StrEnum):
    """Тип изменения остатка на месте."""

    # ВАЖНО: семантика change_amount задается бизнес-логикой:
    # - loading: забрали с места -> change_amount обычно отрицательный (остаток уменьшается)
    # - unloading: привезли на место -> change_amount обычно положительный (остаток увеличивается)
    loading = "loading"
    unloading = "unloading"
    manual = "manual"  # Ручная корректировка остатка (в т.ч. начальная установка)
