"""Схемы: объёмы по видам груза за текущую смену."""

from pydantic import Field

from app.api.schemas.base import APIBaseModel


class ShiftLoadTypeVolumeRow(APIBaseModel):
    """Одна строка таблицы «итоги по видам груза»."""

    load_type_id: int = Field(..., description="ID вида груза (load_types / cargo_type места погрузки)")
    load_type_name: str = Field(
        ...,
        description="Наименование вида груза; пустая строка, если справочник не вернул имя",
    )
    volume_sections_m3: float = Field(
        ...,
        description=(
            "Объём (м³) по участкам: при переданных section_id — сумма по любому из участков (OR), иначе по всем"
        ),
    )
    volume_places_m3: float = Field(
        ...,
        description=(
            "Объём (м³) по местам разгрузки: при переданных place_id — сумма по любому из мест (OR), иначе по всем"
        ),
    )


class ShiftLoadTypeVolumesResponse(APIBaseModel):
    """Ответ: сводка перевезённого объёма по видам груза за текущую смену."""

    shift_date: str = Field(
        ...,
        description="Дата смены (YYYY-MM-DD); пустая строка, если смену определить не удалось",
    )
    shift_num: int = Field(
        ...,
        description="Номер смены; 0, если смену определить не удалось",
    )
    items: list[ShiftLoadTypeVolumeRow] = Field(
        ...,
        description="Строки по видам груза",
    )
