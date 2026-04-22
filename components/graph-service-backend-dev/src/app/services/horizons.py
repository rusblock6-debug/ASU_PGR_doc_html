"""Сервис для работы с горизонтами (horizons)"""

import logging
from datetime import date
from typing import Any

import sqlalchemy as sa
from geoalchemy2.functions import ST_X, ST_Y, ST_Z
from pydantic import TypeAdapter
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload, selectinload, with_polymorphic

from app.models.database import (
    GraphEdge,
    GraphNode,
    Horizon,
    Ladder,
    LoadPlace,
    ParkPlace,
    Place,
    ReloadPlace,
    Shaft,
    Tag,
    TransitPlace,
    UnloadPlace,
)
from app.schemas.edges import EdgeResponse
from app.schemas.graph_datas import GraphData
from app.schemas.horizons import (
    HorizonCreate,
    HorizonGraphBulkUpsertClientEdge,
    HorizonGraphBulkUpsertClientNode,
    HorizonGraphBulkUpsertRequest,
    HorizonGraphBulkUpsertServerEdge,
    HorizonGraphBulkUpsertServerNode,
    HorizonListResponse,
    HorizonUpdate,
)
from app.schemas.horizons import (
    HorizonResponse as HorizonSchema,
)
from app.schemas.ladders import LadderResponse
from app.schemas.nodes import NodeResponse
from app.schemas.places import PlaceResponse
from app.schemas.tags import APITagResponseModel
from app.services.places import section_ids_for_place

logger = logging.getLogger(__name__)


class HorizonService:
    """Сервис для работы с горизонтами"""

    async def get_horizons(
        self,
        db: AsyncSession,
        page: int | None = None,
        size: int | None = None,
    ) -> HorizonListResponse:
        """Получить список всех горизонтов.

        Если параметры page и size не указаны — возвращает все записи.
        Если указан хотя бы один — применяется пагинация.
        """
        # Если пагинация отключена (page и size не указаны)
        if page is None and size is None:
            result = await db.execute(select(Horizon).order_by(Horizon.id))
            horizons = result.scalars().all()
            items_count = len(horizons)
            return HorizonListResponse(
                total=items_count,
                page=1,
                size=items_count if items_count > 0 else 1,
                items=[HorizonSchema.model_validate(h) for h in horizons],
            )
        else:
            # Пагинация включена — устанавливаем дефолтные значения
            page = page or 1
            size = size or 20

            total = await db.scalar(select(func.count()).select_from(Horizon))
            offset = (page - 1) * size
            result = await db.execute(
                select(Horizon).order_by(Horizon.id).offset(offset).limit(size),
            )
            horizons = result.scalars().all()

            return HorizonListResponse(
                total=total or 0,
                page=page,
                size=size,
                items=[HorizonSchema.model_validate(h) for h in horizons],
            )

    async def create_horizon(
        self,
        db: AsyncSession,
        level_data: HorizonCreate,
    ) -> HorizonSchema:
        """Создать новый горизонт"""
        horizon_dict = level_data.model_dump(exclude={"shafts"})
        level = Horizon(**horizon_dict)
        db.add(level)
        await db.flush()

        if level_data.shafts:
            result = await db.execute(select(Shaft).where(Shaft.id.in_(level_data.shafts)))
            shafts = result.scalars().all()
            if len(shafts) != len(level_data.shafts):
                found_ids = {s.id for s in shafts}
                missing = [sid for sid in level_data.shafts if sid not in found_ids]
                raise ValueError(f"Шахты не найдены: {missing}")

            # Загружаем level с предзагруженными связями, чтобы избежать lazy loading
            level_result = await db.execute(
                select(Horizon).options(selectinload(Horizon.shafts)).where(Horizon.id == level.id),
            )
            level = level_result.scalar_one()
            level.shafts = list(shafts)

        await db.refresh(level, attribute_names=["shafts"])
        await db.commit()

        return HorizonSchema.model_validate(level)

    async def get_horizon(
        self,
        db: AsyncSession,
        horizon_id: int,
    ) -> HorizonSchema:
        """Получить уровень по ID"""
        result = await db.execute(select(Horizon).where(Horizon.id == horizon_id))
        level = result.scalar_one_or_none()
        if not level:
            raise ValueError(f"Horizon {horizon_id} not found")

        return HorizonSchema.model_validate(level)

    async def get_horizon_objects_count(
        self,
        db: AsyncSession,
        horizon_id: int,
    ) -> dict[str, Any]:
        """Получить количество объектов на горизонте (для предупреждения перед удалением)"""
        result = await db.execute(select(Horizon).where(Horizon.id == horizon_id))
        level = result.scalar_one_or_none()
        if not level:
            raise ValueError(f"Horizon {horizon_id} not found")

        nodes_count = await db.scalar(
            select(func.count()).select_from(GraphNode).where(GraphNode.horizon_id == horizon_id),
        )
        edges_count = await db.scalar(
            select(func.count()).select_from(GraphEdge).where(GraphEdge.horizon_id == horizon_id),
        )
        tags_count = await db.scalar(
            select(func.count())
            .select_from(Tag)
            .join(Place, Tag.place_id == Place.id, isouter=True)
            .join(GraphNode, Place.node_id == GraphNode.id, isouter=True)
            .where(GraphNode.horizon_id == horizon_id),
        )

        # Вертикальные рёбра (лестницы) связанные с узлами этого горизонта
        node_ids_result = await db.execute(
            select(GraphNode.id).where(GraphNode.horizon_id == horizon_id),
        )
        node_ids = [nid for nid in node_ids_result.scalars().all()]

        vertical_edges_count = 0
        if node_ids:
            from sqlalchemy import and_

            vertical_edges_count = await db.scalar(  # type: ignore[assignment]
                select(func.count())
                .select_from(GraphEdge)
                .where(
                    and_(
                        GraphEdge.edge_type == "vertical",
                        or_(
                            GraphEdge.from_node_id.in_(node_ids),
                            GraphEdge.to_node_id.in_(node_ids),
                        ),
                    ),
                ),
            )

        return {
            "horizon_id": horizon_id,
            "level_name": level.name,
            "objects": {
                "nodes": nodes_count or 0,
                "edges": edges_count or 0,
                "tags": tags_count or 0,
                "ladders": vertical_edges_count or 0,
            },
            "total": (nodes_count or 0)
            + (edges_count or 0)
            + (tags_count or 0)
            + (vertical_edges_count or 0),
        }

    async def update_horizon(
        self,
        db: AsyncSession,
        horizon_id: int,
        update_data: HorizonUpdate,
    ) -> HorizonSchema:
        """Обновить параметры горизонта"""
        # Загружаем горизонт с предзагруженными связями, чтобы избежать lazy loading
        result = await db.execute(
            select(Horizon).options(selectinload(Horizon.shafts)).where(Horizon.id == horizon_id),
        )
        level = result.scalar_one_or_none()
        if not level:
            raise ValueError(f"Horizon {horizon_id} not found")

        if update_data.name is not None:
            level.name = update_data.name  # type: ignore[assignment]
        if update_data.height is not None:
            level.height = update_data.height  # type: ignore[assignment]
        if update_data.color is not None:
            level.color = update_data.color  # type: ignore[assignment]

        if update_data.shafts is not None:
            if update_data.shafts:
                shafts_result = await db.execute(
                    select(Shaft).where(Shaft.id.in_(update_data.shafts)),
                )
                shafts = shafts_result.scalars().all()
                if len(shafts) != len(update_data.shafts):
                    found_ids = {s.id for s in shafts}
                    missing = [sid for sid in update_data.shafts if sid not in found_ids]
                    raise ValueError(f"Шахты не найдены: {missing}")
                # Используем прямое присваивание, так как связи уже загружены через selectinload
                level.shafts = list(shafts)
            else:
                level.shafts = []

        await db.commit()
        await db.refresh(level)

        return HorizonSchema.model_validate(level)

    async def delete_horizon(
        self,
        db: AsyncSession,
        horizon_id: int,
    ) -> dict[str, Any]:
        """Удалить уровень со всеми объектами (каскадное удаление)"""
        result = await db.execute(select(Horizon).where(Horizon.id == horizon_id))
        level = result.scalar_one_or_none()
        if not level:
            raise ValueError(f"Horizon {horizon_id} not found")

        level_name = level.name

        # Удаляем теги через places
        tags_result = await db.execute(
            delete(Tag).where(
                Tag.place_id.in_(
                    select(Place.id)
                    .join(GraphNode, Place.node_id == GraphNode.id)
                    .where(GraphNode.horizon_id == horizon_id),
                ),
            ),
        )
        tags_deleted = tags_result.rowcount  # type: ignore[attr-defined]

        # Получаем ID узлов
        node_ids_result = await db.execute(
            select(GraphNode.id).where(GraphNode.horizon_id == horizon_id),
        )
        node_ids = [nid for nid in node_ids_result.scalars().all()]

        # Удаляем рёбра связанные с узлами
        edges_deleted = 0
        if node_ids:
            edges_result = await db.execute(
                delete(GraphEdge).where(
                    or_(
                        GraphEdge.from_node_id.in_(node_ids),
                        GraphEdge.to_node_id.in_(node_ids),
                    ),
                ),
            )
            edges_deleted = edges_result.rowcount  # type: ignore[attr-defined]

        # Удаляем узлы
        nodes_result = await db.execute(
            delete(GraphNode).where(GraphNode.horizon_id == horizon_id),
        )
        nodes_deleted = nodes_result.rowcount  # type: ignore[attr-defined]

        # Удаляем горизонт
        await db.delete(level)
        await db.commit()

        return {
            "message": "Horizon deleted successfully",
            "deleted": {
                "level": level_name,
                "nodes": nodes_deleted,
                "edges": edges_deleted,
                "tags": tags_deleted,
            },
        }

    async def get_horizon_graph(
        self,
        db: AsyncSession,
        horizon_id: int,
    ) -> dict[str, Any]:
        """Получить полный граф горизонта (узлы, ребра, метки, места)"""
        result = await db.execute(select(Horizon).where(Horizon.id == horizon_id))
        level = result.scalar_one_or_none()
        if not level:
            raise ValueError(f"Horizon {horizon_id} not found")

        # Загружаем узлы с извлечением координат из geometry
        nodes_result = await db.execute(
            select(
                GraphNode,
                ST_X(GraphNode.geometry).label("x"),
                ST_Y(GraphNode.geometry).label("y"),
                ST_Z(GraphNode.geometry).label("z"),
            )
            .where(GraphNode.horizon_id == horizon_id)
            .options(joinedload(GraphNode.horizon), selectinload(GraphNode.ladders)),
        )
        nodes_rows = nodes_result.all()
        # Преобразуем в список словарей для NodeResponse
        nodes = []
        node_ids = []
        for row in nodes_rows:
            node = row[0]
            node_ids.append(node.id)
            node_dict = {
                "id": node.id,
                "horizon_id": node.horizon_id,
                "node_type": node.node_type,
                "linked_nodes": node.linked_nodes,
                "ladder_ids": [ladder.id for ladder in node.ladders],
                "created_at": node.created_at,
                "updated_at": node.updated_at,
                "z": float(row.z)
                if row.z is not None
                else (node.horizon.height if node.horizon else 0.0),
                "x": float(row.x),
                "y": float(row.y),
            }
            nodes.append(node_dict)

        edges_result = await db.execute(
            select(GraphEdge).where(
                or_(
                    GraphEdge.horizon_id == horizon_id,
                    GraphEdge.from_node_id.in_(node_ids) if node_ids else False,  # type: ignore[arg-type]
                    GraphEdge.to_node_id.in_(node_ids) if node_ids else False,  # type: ignore[arg-type]
                ),
            ),
        )
        edges = list(edges_result.scalars().all())

        # Получаем place_ids для данного horizon_id
        place_ids_result = await db.execute(
            select(Place.id)
            .join(GraphNode, Place.node_id == GraphNode.id)
            .where(GraphNode.horizon_id == horizon_id),
        )
        place_ids = [pid for pid in place_ids_result.scalars().all()]

        # Получаем теги по place_ids с извлечением координат из geometry для places
        if place_ids:
            tags_result = await db.execute(
                select(
                    Tag,
                    ST_X(Place.geometry).label("place_x"),
                    ST_Y(Place.geometry).label("place_y"),
                )
                .join(Tag.place)
                .options(joinedload(Tag.place).joinedload(Place.horizon))
                .where(Tag.place_id.in_(place_ids)),
            )
        else:
            tags_result = await db.execute(select(Tag).where(False))  # type: ignore[arg-type]

        tags_rows = tags_result.all() if place_ids else []
        tags = []
        for row in tags_rows:
            tag = row[0]
            if tag.place:
                # Извлекаем координаты из geometry
                x_coord = float(row.place_x) if row.place_x is not None else None
                y_coord = float(row.place_y) if row.place_y is not None else None

                # Валидация GPS координат: проверяем, что они в допустимых пределах
                # GPS широта должна быть между -90 и 90, долгота между -180 и 180
                # Если координаты выходят за эти пределы, возможно это Canvas координаты,
                # которые были неправильно сохранены как GPS. Пропускаем такие теги.
                if x_coord is not None and y_coord is not None:
                    if not (-90 <= y_coord <= 90 and -180 <= x_coord <= 180):
                        # Координаты выходят за пределы GPS - пропускаем этот тег
                        logger.warning(
                            f"Skipping tag {tag.id} (place {tag.place_id}): "
                            f"coordinates ({x_coord}, {y_coord}) are not valid GPS coordinates. "
                            f"These appear to be Canvas coordinates, not GPS.",
                        )
                        continue

                # Устанавливаем координаты как атрибуты для использования в from_orm
                tag.place._x_coord = x_coord
                tag.place._y_coord = y_coord
            tags.append(tag)

        # Получаем места для данного горизонта с извлечением координат из geometry
        # Используем отдельные запросы для каждого place для надежности
        place_poly = with_polymorphic(
            Place,
            [LoadPlace, UnloadPlace, ReloadPlace, ParkPlace, TransitPlace],
        )
        places_result = await db.execute(
            select(place_poly)
            .join(GraphNode, place_poly.node_id == GraphNode.id)
            .where(GraphNode.horizon_id == horizon_id)
            .options(selectinload(place_poly.horizon).selectinload(Horizon.sections)),
        )
        places_objects = places_result.scalars().unique().all()

        # Преобразуем в список словарей для PlaceResponse, извлекая координаты для каждого place
        places = []
        for place in places_objects:
            if place is None:
                continue

            try:
                # Используем getattr для безопасного доступа к атрибутам
                place_id = getattr(place, "id", None)
                if place_id is None:
                    logger.warning(f"Place object has no id: {place}, type: {type(place)}")
                    continue  # Пропускаем места без ID

                # Извлекаем координаты из geometry через отдельный запрос
                coords_result = await db.execute(
                    select(
                        ST_X(Place.geometry).label("x"),
                        ST_Y(Place.geometry).label("y"),
                    ).where(Place.id == place_id),
                )
                coords_row = coords_result.first()
                x_coord = float(coords_row.x) if coords_row and coords_row.x is not None else None
                y_coord = float(coords_row.y) if coords_row and coords_row.y is not None else None

                # Валидация GPS координат: проверяем, что они в допустимых пределах
                # GPS широта должна быть между -90 и 90, долгота между -180 и 180
                # Если координаты выходят за эти пределы, возможно это Canvas координаты,
                # которые были неправильно сохранены как GPS. Пропускаем такие места.
                if x_coord is not None and y_coord is not None:
                    if not (-90 <= y_coord <= 90 and -180 <= x_coord <= 180):
                        # Координаты выходят за пределы GPS - пропускаем это место
                        logger.warning(
                            f"Skipping place {place_id} ({getattr(place, 'name', None)}): "
                            f"coordinates ({x_coord}, {y_coord}) are not valid GPS coordinates. "
                            f"These appear to be Canvas coordinates, not GPS.",
                        )
                        continue

                place_name = getattr(place, "name", None)
                place_type = getattr(place, "type", None)
                place_horizon_id = getattr(place, "horizon_id", None)
                cargo_type = getattr(place, "cargo_type", None)
                created_at = getattr(place, "created_at", None)
                updated_at = getattr(place, "updated_at", None)

                # Формируем location с GPS координатами для фронтенда
                location = None
                if x_coord is not None and y_coord is not None:
                    # x_coord и y_coord из ST_X/ST_Y - это GPS координаты (lon, lat)
                    location = {"lon": x_coord, "lat": y_coord}

                place_dict = {
                    "id": place_id,
                    "name": place_name,
                    "type": place_type.value  # type: ignore[union-attr]
                    if hasattr(place_type, "value")
                    else str(place_type)
                    if place_type
                    else None,
                    "x": x_coord,
                    "y": y_coord,
                    "location": location,
                    "horizon_id": place_horizon_id,
                    "section_ids": section_ids_for_place(place),
                    "cargo_type": cargo_type,
                    "created_at": created_at,
                    "updated_at": updated_at,
                }

                # is_active обязателен для union-схем PlaceResponse.
                if place_type and place_type in ("load", "unload", "reload"):
                    end_date = getattr(place, "end_date", None)
                    place_dict["is_active"] = end_date is None or end_date > date.today()
                else:
                    place_dict["is_active"] = True

                # Добавляем поля расширений в зависимости от типа места
                if place_type and place_type in ("load", "unload", "reload"):
                    place_dict["start_date"] = getattr(place, "start_date", None)
                    place_dict["end_date"] = getattr(place, "end_date", None)

                    if place_type == "load":
                        place_dict["current_stock"] = getattr(place, "current_stock", None)
                    elif place_type in ("unload", "reload"):
                        place_dict["capacity"] = getattr(place, "capacity", None)
                        place_dict["current_stock"] = getattr(place, "current_stock", None)

                places.append(place_dict)
            except Exception as e:
                logger.error(f"Error processing place {getattr(place, 'id', 'unknown')}: {e}")
                continue

        node_place_links = []
        if node_ids:
            node_places_result = await db.execute(
                select(Place.node_id, Place.id).where(
                    Place.node_id.in_(node_ids),
                ),
            )
            node_place_links = [
                {"node_id": node_id, "place_id": place_id}
                for node_id, place_id in node_places_result.all()
                if node_id is not None
            ]

        ladders_result = await db.execute(
            select(Ladder).where(
                or_(
                    Ladder.from_horizon_id == horizon_id,
                    Ladder.to_horizon_id == horizon_id,
                ),
            ),
        )
        ladders = ladders_result.scalars().all()
        ladder_ids = [ladder.id for ladder in ladders]

        ladder_nodes: list[dict[str, Any]] = []
        ladder_edges: list[GraphEdge] = []
        ladder_node_place_links: list[dict[str, int]] = []
        if ladder_ids:
            ladder_nodes_result = await db.execute(
                select(
                    GraphNode,
                    ST_X(GraphNode.geometry).label("x"),
                    ST_Y(GraphNode.geometry).label("y"),
                    ST_Z(GraphNode.geometry).label("z"),
                )
                .where(GraphNode.ladders.any(Ladder.id.in_(ladder_ids)))
                .options(joinedload(GraphNode.horizon), selectinload(GraphNode.ladders)),
            )
            ladder_nodes_rows = ladder_nodes_result.all()
            ladder_node_ids: list[int] = []
            for row in ladder_nodes_rows:
                node = row[0]
                ladder_node_ids.append(node.id)
                ladder_nodes.append(
                    {
                        "id": node.id,
                        "horizon_id": node.horizon_id,
                        "node_type": node.node_type,
                        "linked_nodes": node.linked_nodes,
                        "ladder_ids": [ladder.id for ladder in node.ladders],
                        "created_at": node.created_at,
                        "updated_at": node.updated_at,
                        "z": float(row.z)
                        if row.z is not None
                        else (node.horizon.height if node.horizon else 0.0),
                        "x": float(row.x),
                        "y": float(row.y),
                    },
                )

            if ladder_node_ids:
                ladder_edges_result = await db.execute(
                    select(GraphEdge).where(
                        or_(
                            GraphEdge.from_node_id.in_(ladder_node_ids),
                            GraphEdge.to_node_id.in_(ladder_node_ids),
                        ),
                    ),
                )
                ladder_edges = list(ladder_edges_result.scalars().all())

                ladder_node_places_result = await db.execute(
                    select(Place.node_id, Place.id).where(
                        Place.node_id.in_(ladder_node_ids),
                    ),
                )
                ladder_node_place_links = [
                    {"node_id": node_id, "place_id": place_id}
                    for node_id, place_id in ladder_node_places_result.all()
                    if node_id is not None
                ]

        # Добавляем связанные с лестницами узлы/рёбра в общий граф горизонта (без дублей)
        if ladder_nodes:
            existing_node_ids = {node["id"] for node in nodes}
            nodes.extend(node for node in ladder_nodes if node["id"] not in existing_node_ids)

        if ladder_edges:
            existing_edge_ids = {edge.id for edge in edges}
            edges.extend(edge for edge in ladder_edges if edge.id not in existing_edge_ids)

        if ladder_node_place_links:
            existing_node_place_links = {
                (link["node_id"], link["place_id"]) for link in node_place_links
            }
            node_place_links.extend(
                link
                for link in ladder_node_place_links
                if (link["node_id"], link["place_id"]) not in existing_node_place_links
            )

        places_validated = TypeAdapter(list[PlaceResponse]).validate_python(places)

        graph_data = GraphData(
            horizon=HorizonSchema.model_validate(level),
            nodes=[NodeResponse.model_validate(node) for node in nodes],
            edges=[EdgeResponse.model_validate(edge) for edge in edges],
            tags=[APITagResponseModel.from_orm(tag) for tag in tags],
            places=places_validated,
            node_places=node_place_links,
            ladders=[LadderResponse.model_validate(ladder) for ladder in ladders],
        )

        return graph_data.model_dump()

    async def bulk_upsert_horizon_graph(
        self,
        db: AsyncSession,
        horizon_id: int,
        request: HorizonGraphBulkUpsertRequest,
    ) -> bool:
        try:
            # 1) Сортировка nodes и edges на серверные и клиентские
            client_nodes, server_nodes = self._sorted_client_or_server_nodes(request.nodes)
            client_edges, server_edges = self._sorted_client_or_server_edges(request.edges)
            # 2) удаление не перечисленных серверных nodes и edges
            await self._delete_missing_nodes_and_edges(
                db=db,
                horizon_id=horizon_id,
                server_nodes=server_nodes,
                server_edges=server_edges,
            )
            # 3) Upsert nodes
            client_id_map = await self._upsert_nodes(
                db=db,
                horizon_id=horizon_id,
                client_nodes=client_nodes,
                server_nodes=server_nodes,
            )
            # 4) Upsert edge
            await self._upsert_edges(
                db=db,
                horizon_id=horizon_id,
                client_edges=client_edges,
                server_edges=server_edges,
                client_node_id_map=client_id_map,
            )
            await db.commit()
            return True
        except Exception as e:
            logger.error(
                "Failed to bulk upsert horizon graph",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

    @staticmethod
    def _sorted_client_or_server_nodes(
        list_client_or_server_nodes: list[
            HorizonGraphBulkUpsertClientNode | HorizonGraphBulkUpsertServerNode
        ],
    ) -> tuple[list[HorizonGraphBulkUpsertClientNode], list[HorizonGraphBulkUpsertServerNode]]:
        """Сортировка серверных и клиентских нод"""
        try:
            client_nodes: list[HorizonGraphBulkUpsertClientNode] = []
            server_nodes: list[HorizonGraphBulkUpsertServerNode] = []
            for node in list_client_or_server_nodes:
                if isinstance(node.id, int):
                    server_nodes.append(node)  # type: ignore[arg-type]
                else:
                    client_nodes.append(node)  # type: ignore[arg-type]
            return client_nodes, server_nodes
        except Exception as e:
            logger.error(
                "Failed to sorted client or server nodes",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

    @staticmethod
    def _sorted_client_or_server_edges(
        list_client_or_server_edges: list[
            HorizonGraphBulkUpsertServerEdge | HorizonGraphBulkUpsertClientEdge
        ],
    ) -> tuple[list[HorizonGraphBulkUpsertClientEdge], list[HorizonGraphBulkUpsertServerEdge]]:
        """Сортировка серверных и клиентских ребер"""
        try:
            client_edges: list[HorizonGraphBulkUpsertClientEdge] = []
            server_edges: list[HorizonGraphBulkUpsertServerEdge] = []
            for edge in list_client_or_server_edges:
                if isinstance(edge, HorizonGraphBulkUpsertServerEdge):
                    server_edges.append(edge)
                else:
                    client_edges.append(edge)
            return client_edges, server_edges
        except Exception as e:
            logger.error(
                "Failed to sorted client or server edges",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

    @staticmethod
    async def _delete_missing_nodes_and_edges(
        db: AsyncSession,
        horizon_id: int,
        server_nodes: list[HorizonGraphBulkUpsertServerNode],
        server_edges: list[HorizonGraphBulkUpsertServerEdge],
    ) -> None:
        """Удаляет серверных ноды/рёбра, которые не переданы в bulk-upsert запросе."""
        try:
            # Определяем множество id серверных нод и ребер
            incoming_node_ids: set[int] = {n.id for n in server_nodes}
            incoming_edge_ids: set[int] = {e.id for e in server_edges}

            # Получаем список нод которые есть у этого графа на этом горизонте
            existing_node_ids_result = await db.execute(
                select(GraphNode.id).where(GraphNode.horizon_id == horizon_id),
            )
            existing_node_ids: set[int] = {i for i in existing_node_ids_result.scalars().all()}
            node_ids_to_delete = sorted(existing_node_ids - incoming_node_ids)

            # Повторяем то-же самое и для ребер
            existing_edge_ids_result = await db.execute(
                select(GraphEdge.id).where(GraphEdge.horizon_id == horizon_id),
            )
            existing_edge_ids: set[int] = {i for i in existing_edge_ids_result.scalars().all()}
            edge_ids_to_delete = sorted(existing_edge_ids - incoming_edge_ids)

            # Удаление ребер и нод
            if edge_ids_to_delete:
                await db.execute(delete(GraphEdge).where(GraphEdge.id.in_(edge_ids_to_delete)))
            if node_ids_to_delete:
                await db.execute(delete(GraphNode).where(GraphNode.id.in_(node_ids_to_delete)))
        except Exception as e:
            logger.error(
                "Failed to delete missing nodes and edges",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

    @staticmethod
    async def _upsert_nodes(
        db: AsyncSession,
        horizon_id: int,
        client_nodes: list[HorizonGraphBulkUpsertClientNode],
        server_nodes: list[HorizonGraphBulkUpsertServerNode],
    ) -> dict[str, int]:
        """Upsert нод: обновляет координаты существующих (server) и создает новые (client).
        Возвращает mapping client_node_id(str) -> created db node_id(int).
        """
        try:
            # Проверяем есть ли горизонт с таким id
            horizon_height = await db.scalar(select(Horizon.height).where(Horizon.id == horizon_id))
            if horizon_height is None:
                raise ValueError(f"Horizon {horizon_id} not found")

            server_rows = [(n.id, n.x, n.y) for n in server_nodes]
            if server_rows:
                # Создаем виртуальную таблицу
                incoming_nodes = (
                    sa.values(
                        sa.column("id", sa.Integer),
                        sa.column("x", sa.Float),
                        sa.column("y", sa.Float),
                        name="incoming_nodes",
                    )
                    .data(server_rows)
                    .alias("incoming_nodes")
                )
                # Update на значения из виртуальной таблице в бд при условии если есть изменения
                await db.execute(
                    sa.update(GraphNode)
                    .where(GraphNode.horizon_id == horizon_id)
                    .where(GraphNode.id == incoming_nodes.c.id)
                    .where(
                        sa.or_(
                            ST_X(GraphNode.geometry) != incoming_nodes.c.x,
                            ST_Y(GraphNode.geometry) != incoming_nodes.c.y,
                        ),
                    )
                    .values(
                        geometry=func.ST_SetSRID(
                            func.ST_MakePoint(
                                incoming_nodes.c.x,
                                incoming_nodes.c.y,
                                ST_Z(GraphNode.geometry),
                            ),
                            4326,
                        ),
                    ),
                )

            # Создаем ноды из клиентских id (используем высоту горизонта как Z)
            client_id_map: dict[str, int] = {}
            for node in client_nodes:
                client_id = node.id
                db_node = GraphNode(horizon_id=horizon_id, node_type="road")
                db_node.geometry = func.ST_SetSRID(
                    func.ST_MakePoint(node.x, node.y, horizon_height),
                    4326,
                )
                db.add(db_node)
                await db.flush()
                client_id_map[client_id] = db_node.id

            return client_id_map
        except Exception as e:
            logger.error(
                "Failed to upsert nodes",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

    @staticmethod
    async def _upsert_edges(
        db: AsyncSession,
        horizon_id: int,
        client_edges: list[HorizonGraphBulkUpsertClientEdge],
        server_edges: list[HorizonGraphBulkUpsertServerEdge],
        client_node_id_map: dict[str, int],
    ) -> None:
        """Upsert ребер: обновляет существующие (server) и создает новые (client).
        Для client ребер node-id могут быть str, они резолвятся через client_node_id_map.
        """
        try:

            def resolve_node_id(node_id: int | str) -> int:
                """Возвращает id созданной node в бд"""
                if isinstance(node_id, int):
                    return node_id
                mapped = client_node_id_map.get(node_id)
                if mapped is None:
                    raise ValueError(f"Client node id {node_id} not found in mapping")
                return mapped

            resolved_server_rows: list[tuple[int, int, int]] = []
            resolved_client_pairs: list[tuple[int, int]] = []
            needed_node_ids: set[int] = set()

            for server_edge in server_edges:
                from_id = server_edge.from_node_id
                to_id = server_edge.to_node_id
                resolved_server_rows.append((server_edge.id, from_id, to_id))
                needed_node_ids.add(from_id)
                needed_node_ids.add(to_id)

            for client_edge in client_edges:
                from_id = resolve_node_id(client_edge.from_node_id)
                to_id = resolve_node_id(client_edge.to_node_id)
                resolved_client_pairs.append((from_id, to_id))
                needed_node_ids.add(from_id)
                needed_node_ids.add(to_id)

            nodes_by_id: dict[int, GraphNode] = {}
            if needed_node_ids:
                nodes_result = await db.execute(
                    select(GraphNode).where(GraphNode.id.in_(sorted(needed_node_ids))),
                )
                nodes_by_id = {n.id: n for n in nodes_result.scalars().all()}

            # Bulk update server edges (only for this horizon).
            if resolved_server_rows:
                incoming_edges = (
                    sa.values(
                        sa.column("id", sa.Integer),
                        sa.column("from_node_id", sa.Integer),
                        sa.column("to_node_id", sa.Integer),
                        name="incoming_edges",
                    )
                    .data(resolved_server_rows)
                    .alias("incoming_edges")
                )

                fn = aliased(GraphNode)
                tn = aliased(GraphNode)

                await db.execute(
                    sa.update(GraphEdge)
                    .where(GraphEdge.horizon_id == horizon_id)
                    .where(GraphEdge.id == incoming_edges.c.id)
                    .where(fn.id == incoming_edges.c.from_node_id)
                    .where(tn.id == incoming_edges.c.to_node_id)
                    .where(
                        sa.or_(
                            GraphEdge.from_node_id != incoming_edges.c.from_node_id,
                            GraphEdge.to_node_id != incoming_edges.c.to_node_id,
                        ),
                    )
                    .values(
                        from_node_id=incoming_edges.c.from_node_id,
                        to_node_id=incoming_edges.c.to_node_id,
                        geometry=func.ST_MakeLine(fn.geometry, tn.geometry),
                    ),
                )

            # Create new edges.
            for from_id, to_id in resolved_client_pairs:
                from_node = nodes_by_id.get(from_id)
                to_node = nodes_by_id.get(to_id)
                if not from_node:
                    raise ValueError(f"Node {from_id} not found")
                if not to_node:
                    raise ValueError(f"Node {to_id} not found")

                edge = GraphEdge(
                    horizon_id=horizon_id,
                    from_node_id=from_id,
                    to_node_id=to_id,
                    edge_type="horizontal",
                )
                edge.geometry = func.ST_MakeLine(from_node.geometry, to_node.geometry)
                db.add(edge)
        except Exception as e:
            logger.error(
                "Failed to upsert edges",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise


# Глобальный экземпляр сервиса
horizon_service = HorizonService()
