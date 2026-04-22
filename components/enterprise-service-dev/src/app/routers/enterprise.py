"""Enterprise Settings endpoints (refactored)."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import EnterpriseSettings
from app.schemas import EnterpriseSettingsCreate, EnterpriseSettingsUpdate
from app.utils.dependencies import get_db_session

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


def _serialize_datetime(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return datetime.utcnow().isoformat()


def _enterprise_to_dict(ent: EnterpriseSettings) -> dict[str, Any]:
    """Конвертация SQLAlchemy-модели EnterpriseSettings в простую dict-структуру."""
    return {
        "id": ent.id,
        "enterprise_name": ent.enterprise_name,
        "timezone": ent.timezone,
        "address": ent.address,
        "phone": ent.phone,
        "email": ent.email,
        "coordinates": ent.coordinates,
        "settings_data": ent.settings_data,
        "created_at": _serialize_datetime(ent.created_at),
        "updated_at": _serialize_datetime(ent.updated_at),
    }


@router.get("", response_model=list[dict[str, Any]])
async def list_enterprises(db: AsyncSession = Depends(get_db_session)) -> list[dict[str, Any]]:
    """Получить список всех предприятий."""
    result = await db.execute(select(EnterpriseSettings))
    enterprises = result.scalars().all()
    return [_enterprise_to_dict(e) for e in enterprises]


@router.get("/{enterprise_id}")
async def get_enterprise(
    enterprise_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Получить параметры предприятия по ID."""
    result = await db.execute(
        select(EnterpriseSettings).where(EnterpriseSettings.id == enterprise_id),
    )
    enterprise = result.scalar_one_or_none()

    if not enterprise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Предприятие с ID {enterprise_id} не найдено",
        )

    return _enterprise_to_dict(enterprise)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_enterprise(
    data: EnterpriseSettingsCreate,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Создать новое предприятие."""
    enterprise = EnterpriseSettings(**data.model_dump())
    db.add(enterprise)
    await db.commit()
    await db.refresh(enterprise)

    return _enterprise_to_dict(enterprise)


@router.put("/{enterprise_id}")
async def update_enterprise(
    enterprise_id: int,
    data: EnterpriseSettingsUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Обновить параметры предприятия."""
    result = await db.execute(
        select(EnterpriseSettings).where(EnterpriseSettings.id == enterprise_id),
    )
    enterprise = result.scalar_one_or_none()

    if not enterprise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Предприятие с ID {enterprise_id} не найдено",
        )

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(enterprise, key, value)

    await db.commit()
    await db.refresh(enterprise)

    return _enterprise_to_dict(enterprise)


@router.delete("/{enterprise_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_enterprise(
    enterprise_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Удалить предприятие по ID."""
    result = await db.execute(
        select(EnterpriseSettings).where(EnterpriseSettings.id == enterprise_id),
    )
    enterprise = result.scalar_one_or_none()

    if not enterprise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Предприятие с ID {enterprise_id} не найдено",
        )

    await db.delete(enterprise)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
