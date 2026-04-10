"""API endpoints для сервиса смен (ShiftService).

Предоставляет доступ к функционалу расчета смен на основе WorkRegime.
"""

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.shift_service import ShiftService
from app.utils.dependencies import get_db_session

router = APIRouter(prefix="/shift-service", tags=["shift-service"])


@router.get("/get-shift-time-range")
async def get_shift_time_range(
    shift_date: date = Query(..., description="Дата смены"),
    shift_number: int = Query(..., ge=1, description="Номер смены"),
    work_regime_id: int | None = Query(None, description="ID режима работы"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Получить временной диапазон для конкретной смены на конкретную дату.

    Args:
        shift_date: Дата смены
        shift_number: Номер смены (1, 2, 3, etc.)
        work_regime_id: ID режима работы (если None - берем первую активную запись)
        db: Сессия базы данных.

    Returns:
        Словарь с 'start_time' и 'end_time' или None если смена не найдена
    """
    try:
        result = await ShiftService.get_shift_time_range(
            shift_date=shift_date,
            shift_number=shift_number,
            work_regime_id=work_regime_id,
            db=db,
        )

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shift time range not found",
            )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating shift time range: {str(e)}",
        ) from e


@router.get("/get-shift-info-by-timestamp")
async def get_shift_info_by_timestamp(
    timestamp: str = Query(..., description="Timestamp для определения смены (ISO format)"),
    work_regime_id: int | None = Query(
        None,
        description="ID режима работы (если None - берется первый активный)",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Определить shift_date и shift_num для заданного timestamp.

    Args:
        timestamp: Время для определения смены
        work_regime_id: ID режима работы (если None - берется первый активный)
        db: Сессия базы данных.

    Returns:
        Словарь с shift_date и shift_num или None если не найдено
    """
    try:
        try:
            parsed_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid timestamp format: {str(e)}",
            ) from e

        result = await ShiftService.get_shift_info_by_timestamp(
            timestamp=parsed_timestamp,
            work_regime_id=work_regime_id,
            db=db,
        )

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shift info not found for given timestamp",
            )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error determining shift info: {str(e)}",
        ) from e


@router.get("/prev-shift")
async def get_prev_shift(
    work_regime_id: int = Query(..., description="ID режима работы"),
    current_shift_number: int = Query(..., ge=1, description="Текущий номер смены"),
    current_date: date = Query(..., description="Текущая дата"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Получить информацию о предыдущей смене для указанного режима работы.

    Вызывает ShiftService.get_prev_shift() для расчета предыдущей смены
    на основе WorkRegime.shifts_definition.

    Args:
        work_regime_id: ID режима работы
        current_shift_number: Текущий номер смены
        current_date: Текущая дата
        db: Сессия базы данных.

    Returns:
        Информация о предыдущей смене (date, shift_number, и др.)
    """
    try:
        result = await ShiftService.get_prev_shift(
            work_regime_id=work_regime_id,
            current_shift_number=current_shift_number,
            current_date=current_date,
            db=db,
        )

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Previous shift not found",
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting previous shift: {str(e)}",
        ) from e
