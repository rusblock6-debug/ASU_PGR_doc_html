"""Сервис для работы с рёбрами графа (edges)"""

"""
Сервис для работы с рёбрами графа (edges)
"""
import json
import logging
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.enum.edges import RoadDirectionEnum
from app.models.database import GraphEdge, GraphNode, Horizon
from app.schemas.edges import EdgeCreate, EdgeResponse
from app.schemas.nodes import NodeResponse

logger = logging.getLogger(__name__)


class EdgeService:
    """Сервис для работы с рёбрами графа"""

    async def get_edge_by_id(self, db: AsyncSession, edge_id: int) -> EdgeResponse:
        result = await db.execute(select(GraphEdge).where(GraphEdge.id == edge_id))
        edge = result.scalar_one_or_none()
        if not edge:
            raise ValueError(f"Edge {edge_id} not found")
        return EdgeResponse.model_validate(edge)

    async def create_edge(
        self,
        db: AsyncSession,
        edge_data: EdgeCreate,
    ) -> EdgeResponse:
        """Создать новое ребро графа"""
        if edge_data.horizon_id is not None:
            horizon = await db.scalar(select(Horizon).where(Horizon.id == edge_data.horizon_id))
            if not horizon:
                raise ValueError(f"Horizon {edge_data.horizon_id} not found")

        from_node = await db.get(GraphNode, edge_data.from_node_id)
        to_node = await db.get(GraphNode, edge_data.to_node_id)
        if not from_node:
            raise ValueError(f"Node {edge_data.from_node_id} not found")
        if not to_node:
            raise ValueError(f"Node {edge_data.to_node_id} not found")

        edge_dict = edge_data.model_dump()
        # Если указан id, используем его (для синхронизации с сервером)
        if edge_data.id is not None:
            edge = GraphEdge(
                id=edge_data.id,
                from_node_id=edge_dict["from_node_id"],
                to_node_id=edge_dict["to_node_id"],
                edge_type=edge_dict.get("edge_type", "horizontal"),
                direction=edge_dict.get("direction", RoadDirectionEnum.bidirectional.value),
                horizon_id=edge_dict.get("horizon_id"),
            )
        else:
            # Обычное создание с автоинкрементом
            edge = GraphEdge(**{k: v for k, v in edge_dict.items() if k != "id"})
        edge.geometry = func.ST_MakeLine(from_node.geometry, to_node.geometry)  # type: ignore[assignment]

        db.add(edge)
        await db.commit()
        await db.refresh(edge)
        return EdgeResponse.model_validate(edge)

    async def update_edge(
        self,
        db: AsyncSession,
        edge_id: int,
        update_data: dict[str, Any],
    ) -> EdgeResponse:
        result = await db.execute(select(GraphEdge).where(GraphEdge.id == edge_id))
        edge = result.scalar_one_or_none()
        if not edge:
            raise ValueError(f"Edge {edge_id} not found")

        from_node_id = update_data.get("from_node_id", edge.from_node_id)
        to_node_id = update_data.get("to_node_id", edge.to_node_id)

        from_node = await db.get(GraphNode, from_node_id)
        to_node = await db.get(GraphNode, to_node_id)
        if not from_node:
            raise ValueError(f"Node {from_node_id} not found")
        if not to_node:
            raise ValueError(f"Node {to_node_id} not found")

        edge.from_node_id = from_node_id  # type: ignore[assignment]
        edge.to_node_id = to_node_id  # type: ignore[assignment]
        if "edge_type" in update_data:
            edge.edge_type = update_data["edge_type"]
        if "direction" in update_data:
            edge.direction = update_data["direction"]

        edge.geometry = func.ST_MakeLine(from_node.geometry, to_node.geometry)  # type: ignore[assignment]

        await db.commit()
        await db.refresh(edge)
        return EdgeResponse.model_validate(edge)

    async def delete_edge(
        self,
        db: AsyncSession,
        edge_id: int,
    ) -> dict[str, str]:
        """Удалить ребро графа"""
        result = await db.execute(select(GraphEdge).where(GraphEdge.id == edge_id))
        edge = result.scalar_one_or_none()

        if not edge:
            raise ValueError(f"Edge {edge_id} not found")

        from_node_id = edge.from_node_id  # type: ignore[assignment]
        to_node_id = edge.to_node_id  # type: ignore[assignment]
        # Лестничные (межгоризонтные) связи определяем по отсутствию horizon_id.
        is_ladder_edge = edge.horizon_id is None

        await db.delete(edge)
        await db.flush()

        if is_ladder_edge:
            for node_id in [from_node_id, to_node_id]:
                node = await db.get(GraphNode, node_id)
                if not node:
                    continue

                other_ladder_edges_result = await db.execute(
                    select(func.count())
                    .select_from(GraphEdge)
                    .where(
                        and_(
                            or_(
                                GraphEdge.from_node_id == node_id,
                                GraphEdge.to_node_id == node_id,
                            ),
                            GraphEdge.horizon_id.is_(None),
                        ),
                    ),
                )
                other_ladder_edges = other_ladder_edges_result.scalar() or 0

                if other_ladder_edges == 0:
                    if node.node_type == "ladder":
                        node.node_type = "road"  # type: ignore[assignment]

                    if node.linked_nodes:
                        try:
                            linked_data = json.loads(str(node.linked_nodes))
                            linked_data = {
                                k: v
                                for k, v in linked_data.items()
                                if v != from_node_id and v != to_node_id
                            }
                            node.linked_nodes = json.dumps(linked_data) if linked_data else None  # type: ignore[assignment]
                        except Exception:
                            node.linked_nodes = None  # type: ignore[assignment]

                    db.add(node)

        await db.commit()

        return {"status": "success", "message": "Edge deleted successfully"}

    async def split_edge(
        self,
        db: AsyncSession,
        edge_id: int,
        x: float,
        y: float,
        node_type: str = "junction",
        node_id: int | None = None,
    ) -> dict[str, Any]:
        """Разрезать ребро в указанной точке:
        - создать новый узел;
        - удалить исходное ребро;
        - создать два новых ребра.
        """
        edge = await db.get(GraphEdge, edge_id)
        if not edge:
            raise ValueError(f"Edge {edge_id} not found")

        if edge.horizon_id is None:
            raise ValueError("Cannot split ladder connection edge")

        from_node = await db.get(GraphNode, edge.from_node_id)
        to_node = await db.get(GraphNode, edge.to_node_id)
        if not from_node or not to_node:
            raise ValueError("Source edge contains invalid node references")

        horizon = await db.get(Horizon, edge.horizon_id)
        if not horizon:
            raise ValueError(f"Horizon {edge.horizon_id} not found")

        new_node = GraphNode(
            horizon_id=edge.horizon_id,
            node_type=node_type,
        )
        if node_id is not None:
            new_node.id = node_id  # type: ignore[assignment]
        new_node.geometry = func.ST_SetSRID(
            func.ST_MakePoint(float(x), float(y), float(horizon.height)),
            4326,
        )  # type: ignore[assignment]
        db.add(new_node)
        try:
            await db.flush()
        except IntegrityError as e:
            raise ValueError(f"Failed to create split node: {str(e)}") from e

        first_edge = GraphEdge(
            horizon_id=edge.horizon_id,
            from_node_id=from_node.id,
            to_node_id=new_node.id,
            edge_type=edge.edge_type,
            direction=edge.direction,
        )
        first_edge.geometry = func.ST_MakeLine(from_node.geometry, new_node.geometry)  # type: ignore[assignment]

        second_edge = GraphEdge(
            horizon_id=edge.horizon_id,
            from_node_id=new_node.id,
            to_node_id=to_node.id,
            edge_type=edge.edge_type,
            direction=edge.direction,
        )
        second_edge.geometry = func.ST_MakeLine(new_node.geometry, to_node.geometry)  # type: ignore[assignment]

        db.add(first_edge)
        db.add(second_edge)
        await db.delete(edge)
        await db.commit()

        await db.refresh(new_node)
        await db.refresh(first_edge)
        await db.refresh(second_edge)

        return {
            "deleted_edge_id": edge_id,
            "node": NodeResponse.model_validate(new_node).model_dump(),
            "edges": [
                EdgeResponse.model_validate(first_edge).model_dump(),
                EdgeResponse.model_validate(second_edge).model_dump(),
            ],
        }

    async def batch_update_edges(
        self,
        db: AsyncSession,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        updated = []
        for item in items:
            edge_id = item["id"]
            payload = {k: v for k, v in item.items() if k != "id" and v is not None}
            updated_edge = await self.update_edge(db, edge_id=edge_id, update_data=payload)
            updated.append(updated_edge.model_dump())

        return {"updated_count": len(updated), "items": updated}

    async def batch_delete_edges(
        self,
        db: AsyncSession,
        edge_ids: list[int],
    ) -> dict[str, Any]:
        deleted = []
        for edge_id in edge_ids:
            await self.delete_edge(db, edge_id)
            deleted.append(edge_id)

        return {"deleted_count": len(deleted), "ids": deleted}


# Глобальный экземпляр сервиса
edge_service = EdgeService()
