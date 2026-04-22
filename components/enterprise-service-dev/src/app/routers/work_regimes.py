"""Work Regimes endpoints."""

from typing import Any

from auth_lib import Action, Permission, require_permission
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import WorkRegime
from app.schemas import (
    WorkRegimeCreate,
    WorkRegimeListResponse,
    WorkRegimeResponse,
    WorkRegimeUpdate,
)
from app.utils.dependencies import get_db_session

router = APIRouter(prefix="/work-regimes", tags=["work-regimes"])


@router.get(
    "",
    response_model=WorkRegimeListResponse,
    dependencies=[Depends(require_permission((Permission.WORK_TIME_MAP, Action.VIEW)))],
)
async def list_work_regimes(
    enterprise_id: int = Query(1),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Получить список режимов работы с пагинацией."""
    query = select(WorkRegime).where(WorkRegime.enterprise_id == enterprise_id)

    if is_active is not None:
        query = query.where(WorkRegime.is_active == is_active)

    # Подсчёт общего количества
    count_query = select(func.count()).select_from(query.alias())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Пагинация
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": items,
    }


@router.post("", response_model=WorkRegimeResponse, status_code=status.HTTP_201_CREATED)
async def create_work_regime(
    data: WorkRegimeCreate,
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    """Создать новый режим работы."""
    regime = WorkRegime(**data.model_dump())
    db.add(regime)
    await db.commit()
    await db.refresh(regime)
    return regime


@router.get("/{regime_id}", response_model=WorkRegimeResponse)
async def get_work_regime(
    regime_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    """Получить режим работы по ID."""
    result = await db.execute(
        select(WorkRegime).where(WorkRegime.id == regime_id),
    )
    regime = result.scalar_one_or_none()

    if not regime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Режим работы с ID {regime_id} не найден",
        )

    return regime


@router.put("/{regime_id}", response_model=WorkRegimeResponse)
async def update_work_regime(
    regime_id: int,
    data: WorkRegimeUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    """Обновить режим работы."""
    result = await db.execute(
        select(WorkRegime).where(WorkRegime.id == regime_id),
    )
    regime = result.scalar_one_or_none()

    if not regime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Режим работы с ID {regime_id} не найден",
        )

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(regime, key, value)

    await db.commit()
    await db.refresh(regime)
    return regime


@router.delete("/{regime_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_regime(
    regime_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Удалить режим работы (soft delete)."""
    result = await db.execute(
        select(WorkRegime).where(WorkRegime.id == regime_id),
    )
    regime = result.scalar_one_or_none()

    if not regime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Режим работы с ID {regime_id} не найден",
        )

    regime.is_active = False
    await db.commit()
    return None
