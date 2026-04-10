"""Сервис для работы с местами (places)"""

import logging
import math
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, with_polymorphic

from app.core.redis.vehicle import PLACES_SUFFIX, REDIS_KEY_PREFIX
from app.core.redis.vehicle.vehicle_places import get_all_vehicle_places
from app.models.database import (
    GraphNode,
    Horizon,
    LoadPlace,
    ParkPlace,
    Place,
    ReloadPlace,
    Tag,
    TransitPlace,
    UnloadPlace,
)
from app.schemas.places import (
    LoadPlaceCreate,
    ParkPlaceCreate,
    PlaceCreate,
    PlacePatch,
    PlacesPopupResponse,
    ReloadPlaceCreate,
    TransitPlaceCreate,
    UnloadPlaceCreate,
)
from app.services.api.enterprise_service import APIEnterpriseService
from app.services.api.trip_service import APITripService
from config.settings import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)


def geometry_to_dict(geometry) -> dict[str, float] | None:
    """Конвертирует PostGIS geometry в dict с координатами.
    Возвращает {'x': float, 'y': float} или None.
    """
    if geometry is None:
        return None
    # Используем SQL для извлечения координат из geometry
    # В реальности это будет вызвано через SQLAlchemy expression
    return {"x": None, "y": None}  # type: ignore[dict-item]


def coords_to_geometry(x: float | None, y: float | None, z: float = 0.0) -> Any | None:
    """Конвертирует координаты x, y, z в PostGIS geometry.
    Возвращает ST_Point expression или None.
    """
    if x is None or y is None:
        return None
    return func.ST_SetSRID(func.ST_MakePoint(float(x), float(y), float(z)), 4326)


# Общие поля для всех типов мест (load, unload, reload, transit, park)
PLACE_BASE_FIELDS = {
    "id",
    "name",
    "type",
    "node_id",
    "created_at",
    "updated_at",
}

# Поля расширений, специфичные для каждого типа места
PLACE_TYPE_FIELDS = {
    "load": {"start_date", "end_date", "current_stock"},
    "unload": {"start_date", "end_date", "capacity", "current_stock"},
    "reload": {"start_date", "end_date", "capacity", "current_stock"},
}


def section_ids_for_place(place: Any) -> list[int]:
    """IDs участков через horizon → sections (одно место может относиться к нескольким участкам)."""
    horizon = getattr(place, "horizon", None)
    if not horizon:
        return []
    sections = getattr(horizon, "sections", None) or []
    if not sections:
        return []
    try:
        ids: list[int] = []
        for s in sections:
            sid = getattr(s, "id", None)
            if sid is not None:
                ids.append(int(sid))
    except Exception:
        return []
    return sorted(set(ids))


async def serialize_place(place: Place, db: AsyncSession) -> dict[str, Any]:
    """Формирует ответ по месту, скрывая неактуальные поля.
    Использует getattr для безопасного доступа к атрибутам, чтобы избежать lazy loading.
    Конвертирует geometry в dict формат для API.
    """
    # Используем getattr для всех атрибутов, чтобы избежать lazy loading
    place_id = getattr(place, "id", None)
    place_name = getattr(place, "name", None)
    place_type = getattr(place, "type", None)
    geometry = getattr(place, "geometry", None)
    horizon_id = getattr(place, "horizon_id", None)
    cargo_type = getattr(place, "cargo_type", None)
    created_at = getattr(place, "created_at", None)
    updated_at = getattr(place, "updated_at", None)

    # Извлекаем координаты x, y из geometry для API
    x_coord = None
    y_coord = None
    if geometry is not None:
        # Используем SQL для извлечения координат из geometry
        result = await db.execute(
            select(func.ST_X(geometry).label("x"), func.ST_Y(geometry).label("y")),
        )
        row = result.first()
        if row:
            x_coord = float(row.x)
            y_coord = float(row.y)

    # Базовые поля
    filtered: dict[str, Any] = {
        "id": place_id,
        "name": place_name,
        "type": place_type,
        "node_id": getattr(place, "node_id", None),
        "x": x_coord,
        "y": y_coord,
        "location": (
            {"x": x_coord, "y": y_coord, "lat": y_coord, "lon": x_coord}
            if x_coord is not None and y_coord is not None
            else None
        ),
        "horizon_id": horizon_id,
        "section_ids": section_ids_for_place(place),
        "cargo_type": cargo_type,
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }

    # Поля расширений в зависимости от типа места
    if place_type in ("load", "unload", "reload"):
        filtered["start_date"] = getattr(place, "start_date", None)
        filtered["end_date"] = getattr(place, "end_date", None)

        if place_type == "load":
            filtered["current_stock"] = getattr(place, "current_stock", None)
        elif place_type in ("unload", "reload"):
            filtered["capacity"] = getattr(place, "capacity", None)
            filtered["current_stock"] = getattr(place, "current_stock", None)
    else:
        # Унифицированное "быстрое" поле для сайдбара
        filtered["current_stock"] = None

    # Добавляем horizon_name если relationship загружен
    if horizon_id and hasattr(place, "horizon") and getattr(place, "horizon", None):
        horizon = getattr(place, "horizon", None)
        if horizon:
            filtered["horizon_name"] = getattr(horizon, "name", None)

    # Определяем is_active
    if place_type in ("load", "unload", "reload"):
        end_date = getattr(place, "end_date", None)
        filtered["is_active"] = end_date is None or end_date > datetime.now(UTC).date()
    else:
        filtered["is_active"] = True

    filtered["is_editable"] = True

    return filtered


class PlaceService:
    """Сервис для работы с местами"""

    async def list_places(
        self,
        db: AsyncSession,
        page: int | None = None,
        size: int | None = None,
        type: list[str] | None = None,
        types: str | None = None,
        is_active: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, Any]:
        """Получить список мест (places).

        Если параметры page и size не указаны — возвращает все записи.
        Если указан хотя бы один — применяется пагинация.
        """
        # Для обратной совместимости
        if limit is not None:
            size = min(limit, 100)
        if offset is not None and (page is None or page == 1):
            size = size or 20
            page = max(1, (offset // size) + 1)

        type_filters = list(type) if type else []
        if types:
            type_filters.extend([t.strip() for t in types.split(",") if t.strip()])

        apply_active_filter = False
        is_active_filter = None
        if is_active is not None:
            is_active_filter = is_active.lower() in ("true", "1", "yes")
            apply_active_filter = True

        # Используем with_polymorphic для корректной загрузки полиморфных атрибутов
        poly = with_polymorphic(
            Place,
            [LoadPlace, UnloadPlace, ReloadPlace, ParkPlace, TransitPlace],
        )
        q = select(poly).options(
            selectinload(poly.node),
            selectinload(poly.horizon).selectinload(Horizon.sections),
        )

        if type_filters:
            q = q.where(poly.type.in_(type_filters))

        q = q.order_by(poly.id)
        result = await db.execute(q)
        all_places = result.scalars().unique().all()

        if apply_active_filter:
            filtered_places = []
            for place in all_places:
                place_type = place.type

                if place_type in ("transit", "park"):
                    is_place_active = True
                elif place_type in ("load", "unload", "reload"):
                    end_date = getattr(place, "end_date", None)
                    is_place_active = end_date is None or end_date > datetime.now(UTC).date()
                else:
                    is_place_active = False

                if is_place_active == is_active_filter:
                    filtered_places.append(place)

            places = filtered_places
        else:
            places = list(all_places)

        total = len(places)

        # Сериализуем места
        items = []
        for p in places:
            items.append(await serialize_place(p, db))

        # Если пагинация отключена (page и size не указаны)
        if page is None and size is None:
            return {
                "page": 1,
                "pages": 1,
                "size": total if total > 0 else 1,
                "total": total,
                "items": items,
            }
        else:
            # Пагинация включена
            page = page or 1
            size = size or 20

            pages = math.ceil(total / size) if size else 0
            page = min(page, pages) if pages else 1
            offset_calc = (page - 1) * size
            paginated_items = items[offset_calc : offset_calc + size]

            return {
                "page": page,
                "pages": pages,
                "size": size,
                "total": total,
                "items": paginated_items,
            }

    async def list_places_grouped(
        self,
        db: AsyncSession,
        type: list[str] | None = None,
        types: str | None = None,
        is_active: str | None = None,
    ) -> dict[str, Any]:
        """Вернуть места, сгруппированные по типам, для сайдбара редактора.
        Существующий list_places не изменяется (обратная совместимость).
        """
        flat = await self.list_places(
            db=db,
            page=None,
            size=None,
            type=type,
            types=types,
            is_active=is_active,
            limit=None,
            offset=None,
        )

        groups: dict[str, list[dict[str, Any]]] = {}
        for item in flat["items"]:
            place_type = item.get("type", "unknown")
            groups.setdefault(place_type, []).append(item)

        grouped_items = [
            {
                "type": place_type,
                "count": len(items),
                "items": items,
            }
            for place_type, items in groups.items()
        ]

        grouped_items.sort(key=lambda group: str(group["type"]))
        return {
            "total": flat["total"],
            "groups": grouped_items,
        }

    async def create_place(
        self,
        db: AsyncSession,
        body: PlaceCreate,
    ) -> dict[str, Any]:
        """Создать новую точку (Place)"""
        if body.node_id is not None:
            node_result = await db.execute(select(GraphNode).where(GraphNode.id == body.node_id))
            node_exists = node_result.scalar_one_or_none()
            if not node_exists:
                raise ValueError(f"GraphNode not found: {body.node_id}")

        base_fields = {
            "name": body.name,
            "type": body.type,
            "cargo_type": body.cargo_type,
            "node_id": body.node_id,
        }

        # Если указан id, используем его (для синхронизации с сервером)
        if body.id is not None:
            base_fields["id"] = body.id

        place: Place
        if isinstance(body, LoadPlaceCreate):
            place = LoadPlace(
                **base_fields,
                start_date=body.start_date,
                end_date=body.end_date,
                current_stock=body.current_stock,
            )
        elif isinstance(body, UnloadPlaceCreate):
            place = UnloadPlace(
                **base_fields,
                start_date=body.start_date,
                end_date=body.end_date,
                capacity=body.capacity,
                current_stock=body.current_stock,
            )
        elif isinstance(body, ReloadPlaceCreate):
            place = ReloadPlace(
                **base_fields,
                start_date=body.start_date,
                end_date=body.end_date,
                capacity=body.capacity,
                current_stock=body.current_stock,
            )
        elif isinstance(body, ParkPlaceCreate):
            place = ParkPlace(**base_fields)
        elif isinstance(body, TransitPlaceCreate):
            place = TransitPlace(**base_fields)
        else:
            raise ValueError(f"Unknown place type: {body.type!r}")

        db.add(place)

        try:
            await db.commit()

            # Перезагружаем place с полиморфными атрибутами и horizon для корректной сериализации
            poly = with_polymorphic(
                Place,
                [LoadPlace, UnloadPlace, ReloadPlace, ParkPlace, TransitPlace],
            )
            result = await db.execute(
                select(poly)
                .where(poly.id == place.id)
                .options(
                    selectinload(poly.node),
                    selectinload(poly.horizon).selectinload(Horizon.sections),
                ),
            )
            place = result.scalar_one()  # type: ignore[assignment]

        except IntegrityError as e:
            await db.rollback()
            raise ValueError(f"Integrity error: {str(e)}") from e

        # Создание места считается ручным действием диспетчера:
        # если задан стартовый остаток, фиксируем manual историю в trip-service.
        current_stock = getattr(body, "current_stock", None)
        if current_stock is not None and isinstance(
            body,
            (LoadPlaceCreate, UnloadPlaceCreate, ReloadPlaceCreate),
        ):
            await self._notify_trip_service_manual_remaining_history(
                place_id=place.id,
                target_stock=float(current_stock),
                source="dispatcher",
            )

        return await serialize_place(place, db)

    @staticmethod
    async def get_place(
        db: AsyncSession,
        place_id: int,
    ) -> dict[str, Any]:
        """Получить Place по ID"""
        # Используем with_polymorphic для корректной загрузки полиморфных атрибутов
        poly = with_polymorphic(
            Place,
            [LoadPlace, UnloadPlace, ReloadPlace, ParkPlace, TransitPlace],
        )
        result = await db.execute(
            select(poly)
            .where(poly.id == place_id)
            .options(
                selectinload(poly.node),
                selectinload(poly.horizon).selectinload(Horizon.sections),
            ),
        )
        place = result.scalar_one_or_none()
        if not place:
            raise ValueError(f"Place {place_id} not found")

        return await serialize_place(place, db)

    async def update_place(
        self,
        db: AsyncSession,
        place_id: int,
        body: PlacePatch,
    ) -> dict[str, Any]:
        """Частичное обновление Place"""
        # Используем with_polymorphic для корректной загрузки полиморфных атрибутов
        poly = with_polymorphic(
            Place,
            [LoadPlace, UnloadPlace, ReloadPlace, ParkPlace, TransitPlace],
        )
        result = await db.execute(
            select(poly).where(poly.id == place_id).options(selectinload(poly.node)),
        )
        place = result.scalar_one_or_none()
        if not place:
            raise ValueError(f"Place {place_id} not found")

        payload = body.model_dump(exclude_unset=True, by_alias=False)
        source = payload.pop("source", None)

        extension_field_names = (
            "start_date",
            "end_date",
            "capacity",
            "current_stock",
        )

        current_extension_values = {}
        for field in extension_field_names:
            if hasattr(place, field):
                current_extension_values[field] = getattr(place, field)

        extension_updates = {}
        for field in extension_field_names:
            if field in payload:
                extension_updates[field] = payload.pop(field)

        new_type = payload.get("type", place.type)
        place_type_changed = "type" in payload and payload["type"] != place.type

        if "node_id" in payload and payload["node_id"] is not None:
            node_id_val = payload["node_id"]
            node_result = await db.execute(select(GraphNode).where(GraphNode.id == node_id_val))
            node_exists = node_result.scalar_one_or_none()
            if not node_exists:
                raise ValueError(f"GraphNode not found: {payload['node_id']}")

        combined_extension_values = current_extension_values.copy()
        combined_extension_values.update(extension_updates)

        if place_type_changed:
            linked_node_id = place.node_id

            # Собираем ID тегов, привязанных к текущему месту, чтобы переназначить их на новое место
            tag_ids_result = await db.execute(select(Tag.id).where(Tag.place_id == place_id))
            linked_tag_ids = tag_ids_result.scalars().all()

            base_data = {
                "id": place.id,
                "name": place.name,
                "cargo_type": place.cargo_type,
                "node_id": linked_node_id,
            }
            base_data.update({k: v for k, v in payload.items() if k != "type"})

            await db.delete(place)
            await db.flush()

            new_extension_payload = {
                field: combined_extension_values.get(field)
                for field in PLACE_TYPE_FIELDS.get(new_type, set())
                if field in combined_extension_values
            }

            if new_type == "load":
                place = LoadPlace(**base_data, **new_extension_payload)
            elif new_type == "unload":
                place = UnloadPlace(**base_data, **new_extension_payload)
            elif new_type == "reload":
                place = ReloadPlace(**base_data, **new_extension_payload)
            elif new_type == "park":
                place = ParkPlace(**base_data)
            elif new_type == "transit":
                place = TransitPlace(**base_data)
            else:
                raise ValueError(f"Unknown place type: {new_type}")

            db.add(place)
            await db.flush()
            new_place_id = place.id

            # Переназначаем теги со старого места на новое по сохранённым ID
            if linked_tag_ids:
                await db.execute(
                    update(Tag).where(Tag.id.in_(linked_tag_ids)).values(place_id=new_place_id),
                )
        else:
            new_place_id = None
            for field, value in payload.items():
                if hasattr(place, field):
                    setattr(place, field, value)

            for field, value in extension_updates.items():
                if hasattr(place, field):
                    setattr(place, field, value)

        try:
            await db.commit()

            effective_place_id = new_place_id if new_place_id is not None else place_id

            # Ручное изменение остатка (dispatcher) → пишем manual историю в trip-service.
            # Автоматические изменения (system/None) →
            # историю manual НЕ создаём, чтобы не зациклиться.
            if "current_stock" in extension_updates:
                new_stock = extension_updates["current_stock"]
                old_stock = current_extension_values.get("current_stock")

                if new_stock != old_stock and new_stock is not None:
                    if (source or "").lower() == "dispatcher":
                        await self._notify_trip_service_manual_remaining_history(
                            place_id=effective_place_id,
                            target_stock=float(new_stock),
                            source="dispatcher",
                        )

            # Перезагружаем place с полиморфными атрибутами и horizon для корректной сериализации
            poly = with_polymorphic(
                Place,
                [LoadPlace, UnloadPlace, ReloadPlace, ParkPlace, TransitPlace],
            )
            result = await db.execute(
                select(poly)
                .where(poly.id == effective_place_id)
                .options(
                    selectinload(poly.node),
                    selectinload(poly.horizon).selectinload(Horizon.sections),
                ),
            )
            place = result.scalar_one()  # type: ignore[assignment]

        except IntegrityError as e:
            await db.rollback()
            raise ValueError(f"Integrity error: {str(e)}") from e

        return await serialize_place(place, db)

    async def delete_place(
        self,
        db: AsyncSession,
        place_id: int,
    ) -> dict[str, Any]:
        """Удалить Place по ID"""
        place_result = await db.execute(select(Place.id).where(Place.id == place_id))
        if place_result.scalar_one_or_none() is None:
            raise ValueError(f"Place {place_id} not found")

        tag_result = await db.execute(select(Tag).where(Tag.place_id == place_id))
        if tag_result.scalar_one_or_none() is not None:
            raise ValueError(f"Can't delete a place {place_id} because it's associated with a tag")

        await db.execute(delete(Place).where(Place.id == place_id))
        await db.commit()

        return {"message": "Place deleted successfully", "id": place_id}

    async def _notify_trip_service_manual_remaining_history(
        self,
        place_id: int,
        target_stock: float,
        source: str = "dispatcher",
    ) -> None:
        """Создать manual запись истории остатков в trip-service (place_remaining_history)."""
        try:
            trip_url = settings.trip_service_url
            payload = {
                "place_id": place_id,
                "change_type": "manual",
                "target_stock": target_stock,
                "timestamp": datetime.now(UTC).isoformat(),
                "cycle_id": None,
                "task_id": None,
                "shift_id": None,
                "vehicle_id": None,
                "source": source,
            }

            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(f"{trip_url}/api/place-history", json=payload)
                if resp.status_code not in (200, 201):
                    logger.error(f"Failed to create history in trip-service: {resp.status_code}")
                else:
                    logger.info(f"Created history in trip-service for place {place_id}")

        except Exception as e:
            logger.error(f"Error notifying trip-service: {e}")

    @staticmethod
    def get_place_vehicles(place_id: int) -> list[int] | None:
        """Запрашивает у Redis хеши graph-service:vehicle:*:places и возвращает список
        транспортных средств, связанных с указанным местом.
        """
        try:
            raw = get_all_vehicle_places()
            prefix_len = len(REDIS_KEY_PREFIX)

            vehicles: list[int] = []

            for redis_key, data in raw.items():
                if not data:
                    continue

                if redis_key.startswith(REDIS_KEY_PREFIX) and redis_key.endswith(PLACES_SUFFIX):
                    vehicle_id = redis_key[prefix_len : -len(PLACES_SUFFIX)]
                else:
                    vehicle_id = (
                        redis_key[prefix_len:]
                        if redis_key.startswith(REDIS_KEY_PREFIX)
                        else redis_key
                    )
                place_id_val = data.get("place_id")
                if place_id_val is None:
                    continue

                try:
                    vehicle_id_int = int(vehicle_id)
                    place_from_redis = int(place_id_val)
                except (TypeError, ValueError):
                    logger.debug(
                        "Skipping invalid vehicle/place mapping:"
                        " key=%s, vehicle_id=%s, place_id=%s",
                        redis_key,
                        vehicle_id,
                        place_id_val,
                    )
                    continue

                if place_from_redis == place_id:
                    vehicles.append(vehicle_id_int)

            vehicles_sorted = sorted(vehicles)

            return vehicles_sorted
        except Exception as e:
            logger.error(
                "Failed to get vehicles grouped by places from Redis",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

    @staticmethod
    async def get_place_popup(db: AsyncSession, place_id: int) -> PlacesPopupResponse:
        try:
            place = await PlaceService().get_place(db, place_id)

            timestamp_now = datetime.now(UTC).isoformat()
            # Делаем запрос к enterprise service для получения shift_date и shift_num
            shift_info = await APIEnterpriseService().get_shift_info_by_timestamp(
                timestamp=timestamp_now,
            )
            if shift_info is None:
                raise ValueError("Failed to get shift info")
            # Делаем запрос к trip service для получения
            # shift_tasks на определенную дату и номер смены
            shift_tasks_data = await APITripService().get_list_shift_tasks(
                shift_num=shift_info["shift_num"],
                shift_date=shift_info["shift_date"],
            )
            if shift_tasks_data is None:
                raise ValueError("Failed to get shift tasks data")
            # Рассчитываем сколько в этом месте вывезут/выгрузят
            # плановых и фактических тонн за все shift tasks
            (
                planned_trips_all_tons,
                actual_trips_all_tons,
            ) = await PlaceService().get_place_planned_and_actual_trips_all_tons(
                place_id=place_id,
                shift_tasks=shift_tasks_data["items"],
            )

            result = {
                "cargo_type": place["cargo_type"],
                "current_stock": place["current_stock"],
                "planned_value": planned_trips_all_tons,
                "real_value": actual_trips_all_tons,
                "vehicle_id_list": PlaceService().get_place_vehicles(place_id),
            }
            return PlacesPopupResponse.model_validate(result)
        except Exception as e:
            logger.error(
                "Failed to get place popup",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

    @staticmethod
    async def get_place_planned_and_actual_trips_all_tons(
        place_id: int,
        shift_tasks: list[dict[str, Any]],
    ) -> tuple[float, float]:
        """Рассчитываем сколько в этом месте вывезут/выгрузят
        плановых и фактических тонн за все shift tasks

        :param place_id:
        :param shift_tasks:
        :return:
        """
        try:
            planned_trips_all_tons: float = 0
            actual_trips_all_tons: float = 0
            for item_shift_task in shift_tasks:
                # Получение грузоподъемность vehicle
                vehicle_data = await APIEnterpriseService().get_vehicle(
                    vehicle_id=item_shift_task["vehicle_id"],
                )
                if vehicle_data is None:
                    continue
                for item_route_task in item_shift_task["route_tasks"]:
                    if (
                        item_route_task["place_a_id"] == place_id
                        or item_route_task["place_b_id"] == place_id
                    ):
                        planned_trips_all_tons += (
                            item_route_task["planned_trips_count"]
                            * vehicle_data["model"]["load_capacity_tons"]
                        )
                        actual_trips_all_tons += (
                            item_route_task["actual_trips_count"]
                            * vehicle_data["model"]["load_capacity_tons"]
                        )
                    else:
                        continue
            return planned_trips_all_tons, actual_trips_all_tons
        except Exception as e:
            logger.error(
                "Failed to get planned and actual trips all tons",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise


# Глобальный экземпляр сервиса
place_service = PlaceService()
