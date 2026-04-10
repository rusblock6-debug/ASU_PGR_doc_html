import math
from collections.abc import Sequence
from typing import Any

from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload, with_polymorphic
from sqlalchemy.sql import func

from app.models.database import (
    GraphNode,
    LoadPlace,
    ParkPlace,
    Place,
    ReloadPlace,
    Tag,
    TransitPlace,
    UnloadPlace,
)
from app.schemas.tags import APITagCreateModel, APITagUpdateModel
from app.services.crud.base import BaseCRUD
from app.services.places import PLACE_TYPE_FIELDS


class TagsCRUD(BaseCRUD[Tag, APITagCreateModel, APITagUpdateModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(Tag, session)

    async def create_tag(self, tag_data: APITagCreateModel) -> Tag:
        place = await self.session.scalar(
            select(Place).where(Place.id == tag_data.place_id).options(selectinload(Place.node)),
        )
        # horizon = await self.session.scalar(
        #     select(Horizon).where(Horizon.id == tag_data.horizon_id)
        # )
        result = await self.session.scalars(select(Tag.place_id).where(Tag.place_id.isnot(None)))
        place_ids = result.all()

        if tag_data.place_id in place_ids:
            raise ValueError("В выбраном месте метка установлена ранее")

        if place and not place.geometry:
            raise ValueError("В выбраном месте не указаны данные о геометрии")

        # TODO перенести проверку в Place?
        # if not horizon:
        #     raise ValueError(f"Horizon {tag_data.horizon_id} not found")

        # Исключаем tag_id из данных перед созданием объекта Tag
        # tag_data уже является Pydantic моделью после валидации
        tag_dict = tag_data.model_dump(exclude={"tag_id"})
        # Создаем объект Tag напрямую из словаря, минуя create_obj
        # чтобы избежать повторного вызова model_dump()
        session_obj = Tag(**tag_dict)
        self.session.add(session_obj)
        try:
            await self.session.commit()
            await self.session.refresh(session_obj)
            return session_obj
        except Exception:
            await self.session.rollback()
            raise

    async def get_by_id(self, id: int) -> Tag:
        result = await self.session.execute(
            select(
                Tag,
                ST_X(Place.geometry).label("place_x"),
                ST_Y(Place.geometry).label("place_y"),
            )
            .join(Tag.place)
            .where(Tag.id == id)
            .options(
                selectinload(Tag.place).selectinload(Place.horizon),
            ),
        )
        row = result.first()
        if row:
            tag = row[0]
            if tag.place:
                # Устанавливаем координаты как атрибуты для использования в from_orm
                tag.place._x_coord = float(row.place_x) if row.place_x is not None else None
                tag.place._y_coord = float(row.place_y) if row.place_y is not None else None
            return tag
        return None  # type: ignore[return-value]

    async def get_with_relation_for_geo(
        self,
    ) -> Sequence[Tag]:
        smtp = await self.session.scalars(
            select(Tag)
            .join(Tag.place)
            .join(GraphNode, Place.node_id == GraphNode.id)
            .where(
                and_(
                    Tag.place_id.isnot(None),
                    GraphNode.horizon_id.isnot(None),
                ),
            )
            .options(selectinload(Tag.place).selectinload(Place.horizon)),
        )
        return smtp.all()

    async def get_all(self, size: int, page: int) -> Sequence[Tag]:
        skip = page * size if page > 1 else 0
        total = await self.count()
        pages = math.ceil(total / size) if size > 0 else 0
        result = await self.session.execute(
            select(
                Tag,
                ST_X(Place.geometry).label("place_x"),
                ST_Y(Place.geometry).label("place_y"),
            )
            .join(Tag.place)
            .options(joinedload(Tag.place))
            .limit(size)
            .offset(skip)
            .order_by(Tag.id.desc()),
        )
        tags_list = []
        for row in result.all():
            tag = row[0]
            if tag.place:
                # Устанавливаем координаты как атрибуты для использования в from_orm
                tag.place._x_coord = float(row.place_x) if row.place_x is not None else None
                tag.place._y_coord = float(row.place_y) if row.place_y is not None else None
            tags_list.append(tag)
        return total, pages, tags_list  # type: ignore[return-value]

    async def update_tag(self, tag_id: int, update_data: APITagUpdateModel) -> Tag:
        """Обновить метку с поддержкой обновления координат места и изменения типа места"""
        tag = await self.get(tag_id)
        if not tag:
            raise ValueError(f"Tag {tag_id} not found")

        # Получаем данные для обновления, исключая поля для обновления места
        update_dict = update_data.model_dump(
            exclude_unset=True,
            exclude={
                "x",
                "y",
                "name",
                "beacon_place",
                "point_type",
                "beacon_mac",
                "beacon_id",
                "point_id",
            },
        )

        # Обновляем поля метки
        for field, value in update_dict.items():
            if hasattr(tag, field) and value is not None:
                setattr(tag, field, value)

        # Обрабатываем обновление координат места через x, y
        if update_data.x is not None or update_data.y is not None:
            if not tag.place_id:
                raise ValueError("Tag has no place_id, cannot update coordinates")

            # Получаем место
            place = await self.session.scalar(
                select(Place).where(Place.id == tag.place_id).options(selectinload(Place.node)),
            )
            if not place:
                raise ValueError(f"Place {tag.place_id} not found")

            # Получаем текущие координаты если x или y не указаны
            if update_data.x is None or update_data.y is None:
                result = await self.session.execute(
                    select(
                        ST_X(Place.geometry).label("x"),
                        ST_Y(Place.geometry).label("y"),
                    ).where(Place.id == tag.place_id),
                )
                row = result.first()
                current_x = float(row.x) if row and row.x is not None else None
                current_y = float(row.y) if row and row.y is not None else None
            else:
                current_x = None
                current_y = None

            new_x = update_data.x if update_data.x is not None else current_x
            new_y = update_data.y if update_data.y is not None else current_y

            if new_x is not None and new_y is not None:
                if place.node_id is None:
                    raise ValueError("Place has no node_id, cannot update geometry")
                await self.session.execute(
                    update(GraphNode)
                    .where(GraphNode.id == int(place.node_id))
                    .values(
                        geometry=func.ST_SetSRID(
                            func.ST_MakePoint(
                                float(new_x),
                                float(new_y),
                                func.ST_Z(GraphNode.geometry),
                            ),
                            4326,
                        ),
                    ),
                )

        # Обрабатываем изменение типа места через point_type
        # (обрабатываем это ДО обновления названия, чтобы название применилось к новому месту)
        if update_data.point_type and tag.place_id:
            # Маппинг point_type (из API) в PlaceTypeEnum
            point_type_to_place_type = {
                "loading": "load",
                "unloading": "unload",
                "transfer": "reload",
                "transit": "transit",
                "transport": "park",
            }

            # Нормализуем point_type (на случай если пришел старый формат)
            normalized_point_type = update_data.point_type.lower().strip()
            if normalized_point_type in point_type_to_place_type:
                new_place_type = point_type_to_place_type[normalized_point_type]
            else:
                # Если тип не распознан, используем transit по умолчанию
                new_place_type = "transit"

            # Получаем текущее место с полиморфной загрузкой
            poly = with_polymorphic(
                Place,
                [LoadPlace, UnloadPlace, ReloadPlace, ParkPlace, TransitPlace],
            )
            result = await self.session.execute(
                select(poly).where(poly.id == tag.place_id).options(selectinload(poly.node)),
            )
            place = result.scalar_one_or_none()

            if place:
                current_place_type = (
                    place.type.value if hasattr(place.type, "value") else str(place.type)
                )

                # Если тип изменился, нужно пересоздать место с новым типом
                if new_place_type != current_place_type:
                    # Получаем координаты: приоритет у переданных
                    # в запросе x, y, иначе текущие из geometry
                    final_x = None
                    final_y = None

                    # Если координаты переданы в запросе, используем их
                    if update_data.x is not None and update_data.y is not None:
                        final_x = update_data.x
                        final_y = update_data.y
                    else:
                        # Иначе получаем текущие координаты из geometry
                        coords_result = await self.session.execute(
                            select(
                                ST_X(Place.geometry).label("x"),
                                ST_Y(Place.geometry).label("y"),
                            ).where(Place.id == tag.place_id),
                        )
                        coords_row = coords_result.first()
                        if coords_row:
                            final_x = float(coords_row.x) if coords_row.x is not None else None
                            final_y = float(coords_row.y) if coords_row.y is not None else None

                    # Сохраняем текущие значения расширенных полей
                    current_extension_values = {}
                    for field in PLACE_TYPE_FIELDS.get(current_place_type, set()):
                        if hasattr(place, field):
                            current_extension_values[field] = getattr(place, field)

                    # Определяем новое название места (приоритет у переданного в запросе)
                    new_name = None
                    if update_data.name or update_data.beacon_place:
                        new_name = update_data.name or update_data.beacon_place

                    # Подготавливаем данные для нового места
                    base_data = {
                        "name": new_name if new_name else place.name,
                        "cargo_type": place.cargo_type,
                        "node_id": place.node_id,
                    }

                    # Подготавливаем расширенные поля для нового типа
                    new_extension_payload = {
                        field: current_extension_values.get(field)
                        for field in PLACE_TYPE_FIELDS.get(new_place_type, set())
                        if field in current_extension_values
                    }

                    # Удаляем старое место
                    await self.session.delete(place)
                    await self.session.flush()

                    # Создаем новое место нужного типа
                    new_place: Place
                    if new_place_type == "load":
                        new_place = LoadPlace(**base_data, **new_extension_payload)
                    elif new_place_type == "unload":
                        new_place = UnloadPlace(**base_data, **new_extension_payload)
                    elif new_place_type == "reload":
                        new_place = ReloadPlace(**base_data, **new_extension_payload)
                    elif new_place_type == "park":
                        new_place = ParkPlace(**base_data)
                    elif new_place_type == "transit":
                        new_place = TransitPlace(**base_data)
                    else:
                        raise ValueError(f"Unknown place type: {new_place_type}")

                    # Обновляем geometry узла, если координаты известны
                    if final_x is not None and final_y is not None:
                        if new_place.node_id is None:
                            raise ValueError("Place has no node_id, cannot update geometry")
                        await self.session.execute(
                            update(GraphNode)
                            .where(GraphNode.id == int(new_place.node_id))
                            .values(
                                geometry=func.ST_SetSRID(
                                    func.ST_MakePoint(
                                        float(final_x),
                                        float(final_y),
                                        func.ST_Z(GraphNode.geometry),
                                    ),
                                    4326,
                                ),
                            ),
                        )
                    else:
                        raise ValueError("Cannot change place type: coordinates are missing")

                    # Сохраняем новое место
                    self.session.add(new_place)
                    await self.session.flush()

                    # Обновляем place_id в теге на новое место
                    tag.place_id = new_place.id  # type: ignore[assignment]
                elif update_data.name or update_data.beacon_place:
                    # Если тип не изменился, но изменилось название, обновляем название места
                    new_name = update_data.name or update_data.beacon_place
                    if new_name:
                        place.name = new_name

        # Обрабатываем обновление названия места через name или beacon_place
        # (только если point_type не был передан, иначе название уже обработано выше)
        if (
            (update_data.name or update_data.beacon_place)
            and tag.place_id
            and not update_data.point_type
        ):
            place = await self.session.scalar(
                select(Place).where(Place.id == tag.place_id),
            )
            if place:
                new_name = update_data.name or update_data.beacon_place
                if new_name:
                    place.name = new_name

        try:
            await self.session.commit()
            await self.session.refresh(tag)
            # Перезагружаем tag с координатами места для правильной сериализации
            return await self.get_by_id(tag_id)
        except Exception:
            await self.session.rollback()
            raise

    async def delete_obj(self, *, id: Any):
        """Удалить тег."""
        tag = await self.get(id)
        if not tag:
            return None

        await self.session.delete(tag)
        await self.session.commit()

        return tag
