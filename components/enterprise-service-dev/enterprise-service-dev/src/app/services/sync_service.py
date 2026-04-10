"""SyncService - подготовка данных для синхронизации с бортами и полной выгрузки/загрузки."""

from datetime import date, datetime
from typing import Any

import httpx
from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.models import (
    EnterpriseSettings,
    LoadType,
    LoadTypeCategory,
    OrganizationCategory,
    Status,
    Vehicle,
    VehicleModel,
    WorkRegime,
)
from app.enums.statuses import AnalyticCategoryEnum
from app.enums.vehicles import VehicleStatusEnum, VehicleTypeEnum


class SyncService:
    """Сервис для синхронизации данных с бортами."""

    # NOTE: Метод закомментирован, так как ShiftTask и RouteTask находятся в dispa-backend
    # @staticmethod
    # async def prepare_shift_data(
    #     shift_task_id: str,
    #     db: AsyncSession
    # ) -> dict:
    #     """
    #     Подготовить полный пакет данных для отправки на борт.
    #
    #     Включает:
    #     - Информацию о сменном задании
    #     - Информацию о техники
    #     - Маршруты с точками
    #     - Режим работы
    #     - Статусы
    #     """
    #     # Получить сменное задание с relationship
    #     result = await db.execute(
    #         select(ShiftTask)
    #         .options(
    #             selectinload(ShiftTask.work_regime),
    #             selectinload(ShiftTask.vehicle),
    #             selectinload(ShiftTask.route_tasks)
    #         )
    #         .where(ShiftTask.id == shift_task_id)
    #     )
    #     shift_task = result.scalar_one_or_none()
    #
    #     if not shift_task:
    #         raise ValueError(f"ShiftTask {shift_task_id} not found")
    #
    #     # Получить статусы
    #     statuses_result = await db.execute(
    #         select(Status).where(Status.is_active == True)
    #     )
    #     statuses = statuses_result.scalars().all()
    #
    #     # Сформировать пакет данных
    #     sync_data = {
    #         "shift_task": {
    #             "task_id": str(shift_task.id),
    #             "vehicle_id": str(shift_task.vehicle_id),
    #             "work_regime_id": str(shift_task.work_regime_id),
    #             "shift_date": shift_task.shift_date.isoformat(),
    #             "task_name": shift_task.task_name,
    #             "priority": shift_task.priority,
    #             "status": shift_task.status
    #         },
    #         "work_regime": {
    #             "regime_id": str(shift_task.work_regime.id),
    #             "name": shift_task.work_regime.name,
    #             "shifts_definition": shift_task.work_regime.shifts_definition
    #         },
    #         "vehicle": {
    #             "vehicle_id": str(shift_task.vehicle.id),
    #             "vehicle_type": shift_task.vehicle.vehicle_type,
    #             "name": shift_task.vehicle.name,
    #             "model": shift_task.vehicle.model,
    #             "registration_number": shift_task.vehicle.registration_number
    #         },
    #         "route_tasks": [
    #             {
    #                 "route_task_id": str(rt.id),
    #                 "route_order": rt.route_order,
    #                 "place_a_id": rt.place_a_id,
    #                 "place_b_id": rt.place_b_id,
    #                 "planned_trips_count": rt.planned_trips_count,
    #                 "status": str(rt.status)  # Enum автоматически преобразуется в строку
    #             }
    #             for rt in shift_task.route_tasks
    #         ],
    #         "statuses": [
    #             {
    #                 "status_id": str(s.id),
    #                 "name": s.name,
    #                 "color": s.color,
    #                 "export_code": s.export_code,
    #                 "category": s.status_category
    #             }
    #             for s in statuses
    #         ]
    #     }
    #
    #     logger.info(
    #         "Shift data prepared for sync",
    #         shift_task_id=shift_task_id,
    #         routes_count=len(shift_task.route_tasks)
    #     )
    #     return sync_data
    # -------------------------------
    # Full export/import for board sync
    # -------------------------------
    @staticmethod
    def _serialize_datetime(value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if value:
            return datetime.fromisoformat(value)
        return None

    @staticmethod
    def _parse_date(value: str | date | None) -> date | None:
        if isinstance(value, date):
            return value
        if value:
            return date.fromisoformat(value)
        return None

    @staticmethod
    def _vehicle_type(value: str | VehicleTypeEnum | None) -> VehicleTypeEnum | None:
        if value is None:
            return None
        if isinstance(value, VehicleTypeEnum):
            return value
        return VehicleTypeEnum(value)

    @staticmethod
    def _vehicle_status(value: str | VehicleStatusEnum | None) -> VehicleStatusEnum | None:
        if value is None:
            return None
        if isinstance(value, VehicleStatusEnum):
            return value
        return VehicleStatusEnum(value)

    @staticmethod
    def _analytic_category(value: str | AnalyticCategoryEnum | None) -> AnalyticCategoryEnum | None:
        if value is None:
            return None
        if isinstance(value, AnalyticCategoryEnum):
            return value
        return AnalyticCategoryEnum(value)

    @staticmethod
    async def export_full_snapshot(db: AsyncSession) -> dict[str, list[dict[str, Any]]]:
        """Собрать полный срез данных для бортовой синхронизации."""
        enterprise_settings = (await db.execute(select(EnterpriseSettings))).scalars().all()
        work_regimes = (await db.execute(select(WorkRegime))).scalars().all()
        vehicle_models = (await db.execute(select(VehicleModel))).scalars().all()
        vehicles = (await db.execute(select(Vehicle))).scalars().all()
        org_categories = (await db.execute(select(OrganizationCategory))).scalars().all()
        statuses = (await db.execute(select(Status))).scalars().all()
        load_type_categories = (await db.execute(select(LoadTypeCategory))).scalars().all()
        load_types = (await db.execute(select(LoadType))).scalars().all()

        snapshot: dict[str, list[dict[str, Any]]] = {
            "enterprise_settings": [
                {
                    "id": es.id,
                    "enterprise_name": es.enterprise_name,
                    "timezone": es.timezone,
                    "address": es.address,
                    "phone": es.phone,
                    "email": es.email,
                    "coordinates": es.coordinates,
                    "settings_data": es.settings_data,
                }
                for es in enterprise_settings
            ],
            "work_regimes": [
                {
                    "id": wr.id,
                    "enterprise_id": wr.enterprise_id,
                    "name": wr.name,
                    "description": wr.description,
                    "is_active": wr.is_active,
                    "shifts_definition": wr.shifts_definition,
                }
                for wr in work_regimes
            ],
            "vehicle_models": [
                {
                    "id": vm.id,
                    "name": vm.name,
                    "max_speed": vm.max_speed,
                    "tank_volume": vm.tank_volume,
                    "load_capacity_tons": vm.load_capacity_tons,
                    "volume_m3": vm.volume_m3,
                }
                for vm in vehicle_models
            ],
            "vehicles": [
                {
                    "id": v.id,
                    "enterprise_id": v.enterprise_id,
                    "vehicle_type": str(v.vehicle_type),
                    "name": v.name,
                    "model_id": v.model_id,
                    "serial_number": v.serial_number,
                    "registration_number": v.registration_number,
                    "status": str(v.status),
                    "is_active": v.is_active,
                    "active_from": v.active_from.isoformat() if v.active_from else None,
                    "active_to": v.active_to.isoformat() if v.active_to else None,
                }
                for v in vehicles
            ],
            "organization_categories": [{"id": oc.id, "name": oc.name} for oc in org_categories],
            "statuses": [
                {
                    "id": s.id,
                    "system_name": s.system_name,
                    "display_name": s.display_name,
                    "color": s.color,
                    "analytic_category": str(s.analytic_category),
                    "organization_category_id": s.organization_category_id,
                    "system_status": s.system_status,
                }
                for s in statuses
            ],
            "load_type_categories": [
                {
                    "id": ltc.id,
                    "name": ltc.name,
                    "is_mineral": ltc.is_mineral,
                }
                for ltc in load_type_categories
            ],
            "load_types": [
                {
                    "id": lt.id,
                    "name": lt.name,
                    "density": lt.density,
                    "color": lt.color,
                    "category_id": lt.category_id,
                }
                for lt in load_types
            ],
        }

        logger.info(
            "Full snapshot prepared",
            enterprise_settings=len(snapshot["enterprise_settings"]),
            work_regimes=len(snapshot["work_regimes"]),
            vehicles=len(snapshot["vehicles"]),
        )
        return snapshot

    @staticmethod
    async def import_full_snapshot(
        snapshot: dict[str, list[dict[str, Any]]],
        db: AsyncSession,
    ) -> dict[str, int]:
        """Полностью заменить локальные данные данными из snapshot."""
        snapshot = snapshot or {}
        summary: dict[str, int] = {
            "enterprise_settings": len(snapshot.get("enterprise_settings", [])),
            "work_regimes": len(snapshot.get("work_regimes", [])),
            "vehicle_models": len(snapshot.get("vehicle_models", [])),
            "vehicles": len(snapshot.get("vehicles", [])),
            "organization_categories": len(snapshot.get("organization_categories", [])),
            "statuses": len(snapshot.get("statuses", [])),
            "load_type_categories": len(snapshot.get("load_type_categories", [])),
            "load_types": len(snapshot.get("load_types", [])),
            "shift_tasks": len(snapshot.get("shift_tasks", [])),
        }

        async with db.begin():
            # Удаляем в порядке зависимостей
            await db.execute(delete(LoadType))
            await db.execute(delete(LoadTypeCategory))
            await db.execute(delete(Status))
            await db.execute(delete(OrganizationCategory))
            await db.execute(delete(Vehicle))
            await db.execute(delete(VehicleModel))
            await db.execute(delete(WorkRegime))
            await db.execute(delete(EnterpriseSettings))

            # Вставляем базовые таблицы
            for es in snapshot.get("enterprise_settings", []):
                db.add(
                    EnterpriseSettings(
                        id=es.get("id"),
                        enterprise_name=es.get("enterprise_name"),
                        timezone=es.get("timezone"),
                        address=es.get("address"),
                        phone=es.get("phone"),
                        email=es.get("email"),
                        coordinates=es.get("coordinates"),
                        settings_data=es.get("settings_data"),
                    ),
                )

            for wr in snapshot.get("work_regimes", []):
                db.add(
                    WorkRegime(
                        id=wr.get("id"),
                        enterprise_id=wr.get("enterprise_id"),
                        name=wr.get("name"),
                        description=wr.get("description"),
                        is_active=wr.get("is_active", True),
                        shifts_definition=wr.get("shifts_definition") or {},
                    ),
                )

            for vm in snapshot.get("vehicle_models", []):
                db.add(
                    VehicleModel(
                        id=vm.get("id"),
                        name=vm.get("name"),
                        max_speed=vm.get("max_speed"),
                        tank_volume=vm.get("tank_volume"),
                        load_capacity_tons=vm.get("load_capacity_tons"),
                        volume_m3=vm.get("volume_m3"),
                    ),
                )

            for v in snapshot.get("vehicles", []):
                db.add(
                    Vehicle(
                        id=v.get("id"),
                        enterprise_id=v.get("enterprise_id"),
                        vehicle_type=SyncService._vehicle_type(v.get("vehicle_type")),
                        name=v.get("name"),
                        model_id=v.get("model_id"),
                        serial_number=v.get("serial_number"),
                        registration_number=v.get("registration_number"),
                        status=SyncService._vehicle_status(
                            v.get("status", VehicleStatusEnum.active),
                        ),
                        is_active=v.get("is_active", True),
                        active_from=SyncService._parse_date(v.get("active_from")),
                        active_to=SyncService._parse_date(v.get("active_to")),
                    ),
                )

            for oc in snapshot.get("organization_categories", []):
                db.add(
                    OrganizationCategory(
                        id=oc.get("id"),
                        name=oc.get("name"),
                    ),
                )

            for st in snapshot.get("statuses", []):
                db.add(
                    Status(
                        id=st.get("id"),
                        system_name=st.get("system_name"),
                        display_name=st.get("display_name"),
                        color=st.get("color"),
                        analytic_category=SyncService._analytic_category(
                            st.get("analytic_category"),
                        ),
                        organization_category_id=st.get("organization_category_id"),
                        system_status=st.get("system_status", False),
                    ),
                )

            for ltc in snapshot.get("load_type_categories", []):
                db.add(
                    LoadTypeCategory(
                        id=ltc.get("id"),
                        name=ltc.get("name"),
                        is_mineral=ltc.get("is_mineral", False),
                    ),
                )

            for lt in snapshot.get("load_types", []):
                db.add(
                    LoadType(
                        id=lt.get("id"),
                        name=lt.get("name"),
                        density=lt.get("density"),
                        color=lt.get("color"),
                        category_id=lt.get("category_id"),
                    ),
                )
        logger.info("Full snapshot imported", **summary)
        return summary

    @staticmethod
    async def fetch_remote_snapshot(
        base_url: str,
        export_path: str,
        timeout: int = 30,
    ) -> dict[str, list[dict[str, Any]]]:
        """Получить snapshot с сервера."""
        if not base_url:
            raise ValueError("Server base url is not set")

        url = base_url.rstrip("/") + export_path
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()

        if not isinstance(payload, dict):
            raise ValueError("Snapshot response is not a JSON object")

        logger.info("Snapshot fetched from server", url=url)
        return payload

    @staticmethod
    async def sync_from_server(
        db: AsyncSession,
        base_url: str,
        export_path: str | None = None,
        timeout: int | None = None,
    ) -> dict[str, int]:
        """Получить данные с сервера и применить их локально."""
        export_path = export_path or settings.SYNC_EXPORT_PATH
        timeout = timeout or settings.SYNC_HTTP_TIMEOUT

        snapshot = await SyncService.fetch_remote_snapshot(
            base_url=base_url,
            export_path=export_path,
            timeout=timeout,
        )
        summary = await SyncService.import_full_snapshot(snapshot, db)
        return summary
