"""Сервис для работы с узлами графа (nodes)"""

import json
import logging
from datetime import datetime
from typing import Any

from geoalchemy2.functions import ST_X, ST_Y, ST_Z
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.database import GraphEdge, GraphNode, Horizon, Ladder, Place
from app.schemas.nodes import NodeCreate, NodeResponse
from app.utils.validation import (
    handle_validation_errors,
    safe_float_conversion,
    validate_node_data,
)
from config.settings import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)


async def detach_ladder_relations(db: AsyncSession, node_id: int) -> tuple[list[int], list[int]]:
    """Разрывает лестничные связи для указанной ноды.
    Возвращает кортеж: (список ID узлов, которые были изменены,
    список ID удалённых вертикальных рёбер).
    """
    node = await db.get(GraphNode, node_id)
    if not node or node.node_type != "ladder":
        return ([], [])

    changed_node_ids: list[int] = []

    vertical_edges_result = await db.execute(
        select(GraphEdge).where(
            or_(
                and_(GraphEdge.from_node_id == node_id, GraphEdge.edge_type == "vertical"),
                and_(GraphEdge.to_node_id == node_id, GraphEdge.edge_type == "vertical"),
            ),
        ),
    )
    vertical_edges = vertical_edges_result.scalars().all()
    deleted_edge_ids = [e.id for e in vertical_edges]

    for edge in vertical_edges:
        other_node_id = edge.to_node_id if edge.from_node_id == node_id else edge.from_node_id
        other_node = await db.get(GraphNode, other_node_id)
        if not other_node:
            continue

        # Чистим linked_nodes
        if other_node.linked_nodes:
            try:
                linked_data = json.loads(str(other_node.linked_nodes))
            except Exception:
                linked_data = {}
            linked_data = {k: v for k, v in linked_data.items() if v != node_id}
            other_node.linked_nodes = json.dumps(linked_data) if linked_data else None  # type: ignore[assignment]

        # Проверяем остальные вертикальные связи
        other_vertical_count_result = await db.execute(
            select(func.count())
            .select_from(GraphEdge)
            .where(
                and_(
                    GraphEdge.edge_type == "vertical",
                    or_(
                        GraphEdge.from_node_id == other_node_id,
                        GraphEdge.to_node_id == other_node_id,
                    ),
                    GraphEdge.id != edge.id,
                ),
            ),
        )
        other_vertical_count = other_vertical_count_result.scalar() or 0
        if other_vertical_count == 0 and other_node.node_type == "ladder":
            other_node.node_type = "road"  # type: ignore[assignment]
            changed_node_ids.append(other_node_id)  # type: ignore[arg-type]
        elif other_node.linked_nodes:
            changed_node_ids.append(other_node_id)  # type: ignore[arg-type]

    # Удаляем сами вертикальные рёбра
    if vertical_edges:
        await db.execute(delete(GraphEdge).where(GraphEdge.id.in_(deleted_edge_ids)))

    return (changed_node_ids, deleted_edge_ids)  # type: ignore[return-value]


class NodeService:
    """Сервис для работы с узлами графа"""

    async def get_node_by_id(self, db: AsyncSession, node_id: int) -> NodeResponse:
        result = await db.execute(
            select(
                GraphNode,
                ST_X(GraphNode.geometry).label("x"),
                ST_Y(GraphNode.geometry).label("y"),
                ST_Z(GraphNode.geometry).label("z"),
            )
            .where(GraphNode.id == node_id)
            .options(joinedload(GraphNode.horizon), selectinload(GraphNode.ladders)),
        )
        row = result.first()
        if not row:
            raise ValueError(f"Node {node_id} not found")
        node = row[0]
        # Создаем dict с данными узла и координатами
        node_dict = {
            "id": node.id,
            "horizon_id": node.horizon_id,
            "node_type": node.node_type,
            "linked_nodes": node.linked_nodes,
            "ladders_ids": [ladder.id for ladder in node.ladders],
            "created_at": node.created_at,
            "updated_at": node.updated_at,
            "z": float(row.z)
            if row.z is not None
            else (node.horizon.height if node.horizon else 0.0),
            "x": float(row.x),
            "y": float(row.y),
        }
        return NodeResponse.model_validate(node_dict)

    async def create_node(
        self,
        db: AsyncSession,
        node_data: NodeCreate,
    ) -> NodeResponse:
        """Создать новый узел графа"""
        horizon = await db.scalar(select(Horizon).where(Horizon.id == node_data.horizon_id))
        if not horizon:
            raise ValueError(f"Horizon {node_data.horizon_id} not found")
        if node_data.node_type == "ladder":
            ladder_id = node_data.ladders_ids[0] if node_data.ladders_ids else None
            ladder = await db.scalar(select(Ladder).where(Ladder.id == ladder_id))
            if not ladder:
                raise ValueError(f"Ladder {ladder_id} not found")

        # Если указан id, проверяем, не существует ли уже узел с таким ID
        if node_data.id is not None:
            existing_node = await db.get(GraphNode, node_data.id)
            if existing_node:
                raise ValueError(
                    f"Node with id {node_data.id} already exists."
                    f" Use PUT /nodes/{node_data.id} to update it.",
                )
        node_dict = node_data.model_dump()
        # Если указан id, используем его (для синхронизации с сервером)
        if node_data.id is not None:
            node = GraphNode(
                id=node_data.id,
                horizon_id=node_dict["horizon_id"],
                node_type=node_dict.get("node_type", "road"),
                linked_nodes=node_dict.get("linked_nodes"),
            )
        else:
            # Обычное создание с автоинкрементом (исключаем x, y так как их больше нет в модели)
            node = GraphNode(
                **{
                    k: v
                    for k, v in node_dict.items()
                    if k not in ("id", "x", "y", "z", "ladders_ids")
                },
            )
        # Высота в geometry (POINTZ): для ladder — входной z, иначе высота горизонта.
        node_z = (
            node_data.z
            if node_data.node_type == "ladder" and node_data.z is not None
            else float(horizon.height)
        )
        node.geometry = func.ST_SetSRID(
            func.ST_MakePoint(float(node_data.x), float(node_data.y), float(node_z)),
            4326,
        )  # type: ignore[assignment]

        db.add(node)
        try:
            await db.flush()
            if node_data.node_type == "ladder" and ladder is not None:
                node.ladders = [ladder]
            await db.commit()
        except IntegrityError as e:
            await db.rollback()
            # Приводим текст ошибки к строке один раз
            error_text = str(getattr(e, "orig", e))
            lowercase_error = error_text.lower()
            # Если пользователь явно задал id и сработало ограничение уникальности —
            # считаем, что конфликт именно по этому id.
            if node_data.id is not None and (
                "duplicate key" in lowercase_error or "unique constraint" in lowercase_error
            ):
                raise ValueError(
                    f"Node with id {node_data.id} already exists."
                    f" Use PUT /nodes/{node_data.id} to update it.",
                ) from e
            # В остальных случаях возвращаем более общее, но честное сообщение
            raise ValueError(
                f"Failed to create node due to database constraint: {error_text}",
            ) from e

        result = await db.execute(
            select(
                GraphNode,
                ST_X(GraphNode.geometry).label("x"),
                ST_Y(GraphNode.geometry).label("y"),
                ST_Z(GraphNode.geometry).label("z"),
            )
            .where(GraphNode.id == node.id)
            .options(joinedload(GraphNode.horizon), selectinload(GraphNode.ladders)),
        )
        row = result.first()
        if row is None:
            raise ValueError(f"Node {node.id} not found after creation")
        node = row[0]
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
        return NodeResponse.model_validate(node_dict)

    async def update_node(
        self,
        db: AsyncSession,
        node_id: int,
        update_data: dict[str, Any],
        skip_ladder_detach: bool = False,
    ) -> NodeResponse:
        """Обновить узел графа"""
        result = await db.execute(select(GraphNode).where(GraphNode.id == node_id))
        node = result.scalar_one_or_none()

        if not node:
            raise ValueError(f"Node {node_id} not found")

        is_valid, errors = validate_node_data(update_data)
        if not is_valid:
            raise ValueError(handle_validation_errors(errors, "Обновление узла"))

        # Обновление типа
        if "node_type" in update_data:
            new_type = update_data["node_type"]
            if node.node_type == "ladder" and new_type != "ladder" and not skip_ladder_detach:
                node.node_type = new_type
                node.ladders = []
                changed_node_ids, deleted_edge_ids = await detach_ladder_relations(db, node_id)
                if settings.is_server_mode:
                    from app.services.event_publisher import event_publisher

                    # Публикуем события для изменённых узлов
                    for cid in changed_node_ids:
                        await event_publisher.publish_entity_changed("node", str(cid), "update")
                    # Публикуем события для удалённых вертикальных рёбер
                    for eid in deleted_edge_ids:
                        await event_publisher.publish_entity_changed("edge", str(eid), "delete")
            else:
                node.node_type = new_type

        if "ladder_id" in update_data:
            ladder_id = update_data["ladder_id"]
            if ladder_id is not None:
                ladder = await db.scalar(select(Ladder).where(Ladder.id == ladder_id))
                if not ladder:
                    raise ValueError(f"Ladder {ladder_id} not found")
                node.ladders = [ladder]
            else:
                node.ladders = []

        if "x" in update_data or "y" in update_data:
            # Получаем текущие координаты из geometry если x или y не указаны
            if "x" not in update_data or "y" not in update_data:
                result = await db.execute(
                    select(ST_X(node.geometry).label("x"), ST_Y(node.geometry).label("y")),
                )
                row = result.first()
                current_x = float(row.x) if row else 0.0
                current_y = float(row.y) if row else 0.0
            else:
                current_x = None
                current_y = None

            z_result = await db.execute(select(ST_Z(node.geometry).label("z")))
            z_row = z_result.first()
            current_z = float(z_row.z) if z_row and z_row.z is not None else 0.0

            new_x = safe_float_conversion(
                update_data.get("x", current_x),
                current_x if current_x is not None else 0.0,
            )
            new_y = safe_float_conversion(
                update_data.get("y", current_y),
                current_y if current_y is not None else 0.0,
            )
            node.geometry = func.ST_SetSRID(  # type: ignore[assignment]
                func.ST_MakePoint(float(new_x or 0.0), float(new_y or 0.0), float(current_z)),
                4326,
            )

            edges_result = await db.execute(
                select(GraphEdge).where(
                    or_(GraphEdge.from_node_id == node_id, GraphEdge.to_node_id == node_id),
                ),
            )
            edges = edges_result.scalars().all()
            for edge in edges:
                from_node = await db.get(GraphNode, edge.from_node_id)
                to_node = await db.get(GraphNode, edge.to_node_id)
                if from_node and to_node:
                    edge.geometry = func.ST_MakeLine(from_node.geometry, to_node.geometry)  # type: ignore[assignment]

        node.updated_at = datetime.utcnow()
        await db.commit()

        result = await db.execute(
            select(
                GraphNode,
                ST_X(GraphNode.geometry).label("x"),
                ST_Y(GraphNode.geometry).label("y"),
                ST_Z(GraphNode.geometry).label("z"),
            )
            .where(GraphNode.id == node_id)
            .options(joinedload(GraphNode.horizon), selectinload(GraphNode.ladders)),
        )
        row = result.first()
        if row is None:
            raise ValueError(f"Node {node_id} not found after update")
        node = row[0]
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
        return NodeResponse.model_validate(node_dict)

    async def delete_node(
        self,
        db: AsyncSession,
        node_id: int,
        skip_ladder_detach: bool = False,
    ) -> dict[str, str]:
        """Удалить узел графа"""
        node = await db.get(GraphNode, node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        changed_node_ids: list[int] = []
        deleted_edge_ids: list[int] = []
        if node.node_type == "ladder" and not skip_ladder_detach:
            changed_node_ids, deleted_edge_ids = await detach_ladder_relations(db, node_id)

        # Удаляем все рёбра, связанные с этой нодой (включая горизонтальные)
        await db.execute(
            delete(GraphEdge).where(
                or_(GraphEdge.from_node_id == node_id, GraphEdge.to_node_id == node_id),
            ),
        )
        await db.delete(node)
        await db.commit()

        if settings.is_server_mode:
            from app.services.event_publisher import event_publisher

            # Публикуем события для изменённых узлов
            for cid in changed_node_ids:
                await event_publisher.publish_entity_changed("node", str(cid), "update")
            # Публикуем события для удалённых вертикальных рёбер (горизонтальные удаляются каскадно)
            for eid in deleted_edge_ids:
                await event_publisher.publish_entity_changed("edge", str(eid), "delete")

        return {"status": "success", "message": "Node deleted successfully"}

    async def get_node_places(self, db: AsyncSession, node_id: int) -> dict[str, Any]:
        node = await db.get(GraphNode, node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        result = await db.execute(
            select(Place.id).where(Place.node_id == node_id).order_by(Place.id),
        )
        place_ids = [pid for pid in result.scalars().all()]
        return {"node_id": node_id, "place_ids": place_ids}

    async def replace_node_places(
        self,
        db: AsyncSession,
        node_id: int,
        place_ids: list[int],
    ) -> dict[str, Any]:
        node = await db.get(GraphNode, node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        unique_place_ids = sorted(set(place_ids))
        if unique_place_ids:
            existing_places_result = await db.execute(
                select(Place.id).where(Place.id.in_(unique_place_ids)),
            )
            found_place_ids = {row[0] for row in existing_places_result.all()}
            missing = [pid for pid in unique_place_ids if pid not in found_place_ids]
            if missing:
                raise ValueError(f"Places not found: {missing}")

        await db.execute(
            update(Place).where(Place.node_id == node_id).values(node_id=None),
        )
        for place_id in unique_place_ids:
            await db.execute(
                update(Place).where(Place.id == place_id).values(node_id=node_id),
            )

        await db.commit()
        return {"node_id": node_id, "place_ids": unique_place_ids}

    async def unlink_node_place(
        self,
        db: AsyncSession,
        node_id: int,
        place_id: int,
    ) -> dict[str, Any]:
        result = await db.execute(
            select(Place).where(
                Place.node_id == node_id,
                Place.id == place_id,
            ),
        )
        place = result.scalar_one_or_none()
        if not place:
            raise ValueError(f"Link node={node_id}, place={place_id} not found")

        place.node_id = None  # type: ignore[assignment]
        await db.commit()
        return {"status": "success", "node_id": node_id, "place_id": place_id}


# Глобальный экземпляр сервиса
node_service = NodeService()
