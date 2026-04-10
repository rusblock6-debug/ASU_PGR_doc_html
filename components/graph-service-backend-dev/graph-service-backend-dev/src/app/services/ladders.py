"""Сервис для работы с лестничными узлами (ladder)"""

import json
import logging
from typing import Any

from sqlalchemy import and_, delete, func, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enum.edges import RoadDirectionEnum
from app.models.database import GraphEdge, GraphNode, Horizon, Ladder, node_ladders
from app.schemas.edges import EdgeResponse
from app.schemas.ladders import (
    LadderCreate,
    LadderListResponse,
    LadderResponse,
    LadderUpdate,
)
from app.services.event_publisher import event_publisher
from app.services.nodes import node_service

logger = logging.getLogger(__name__)


class LadderService:
    """Сервис для работы с лестничными узлами"""

    async def get_ladders(
        self,
        db: AsyncSession,
        page: int | None = None,
        size: int | None = None,
    ) -> LadderListResponse:
        """Получить список лестниц."""
        if page is None and size is None:
            result = await db.execute(select(Ladder).order_by(Ladder.id))
            items = result.scalars().all()
            count = len(items)
            return LadderListResponse(
                total=count,
                page=1,
                size=count if count > 0 else 1,
                items=[LadderResponse.model_validate(item) for item in items],
            )

        page = page or 1
        size = size or 20
        total = await db.scalar(select(func.count()).select_from(Ladder))
        offset = (page - 1) * size
        result = await db.execute(
            select(Ladder).order_by(Ladder.id).offset(offset).limit(size),
        )
        items = result.scalars().all()
        return LadderListResponse(
            total=total or 0,
            page=page,
            size=size,
            items=[LadderResponse.model_validate(item) for item in items],
        )

    async def get_ladder(self, db: AsyncSession, ladder_id: int) -> LadderResponse:
        """Получить лестницу по ID."""
        ladder = await db.get(Ladder, ladder_id)
        if not ladder:
            raise ValueError(f"Ladder {ladder_id} not found")
        return LadderResponse.model_validate(ladder)

    async def create_ladder(
        self,
        db: AsyncSession,
        ladder_data: LadderCreate,
    ) -> LadderResponse:
        """Создать лестницу."""
        from_horizon = await db.get(Horizon, ladder_data.from_horizon_id)
        if not from_horizon:
            raise ValueError(f"Horizon {ladder_data.from_horizon_id} not found")

        to_horizon = await db.get(Horizon, ladder_data.to_horizon_id)
        if not to_horizon:
            raise ValueError(f"Horizon {ladder_data.to_horizon_id} not found")

        if ladder_data.from_horizon_id == ladder_data.to_horizon_id:
            raise ValueError("from_horizon_id and to_horizon_id must be different")

        if ladder_data.id is not None:
            existing = await db.get(Ladder, ladder_data.id)
            if existing:
                raise ValueError(f"Ladder {ladder_data.id} already exists")

        ladder = Ladder(**ladder_data.model_dump(exclude_unset=True))
        db.add(ladder)
        await db.commit()
        await db.refresh(ladder)
        return LadderResponse.model_validate(ladder)

    async def update_ladder(
        self,
        db: AsyncSession,
        ladder_id: int,
        ladder_data: LadderUpdate,
    ) -> LadderResponse:
        """Частично обновить лестницу."""
        ladder = await db.get(Ladder, ladder_id)
        if not ladder:
            raise ValueError(f"Ladder {ladder_id} not found")

        updates = ladder_data.model_dump(exclude_unset=True)
        if "from_horizon_id" in updates:
            from_horizon = await db.get(Horizon, updates["from_horizon_id"])
            if not from_horizon:
                raise ValueError(f"Horizon {updates['from_horizon_id']} not found")

        if "to_horizon_id" in updates:
            to_horizon = await db.get(Horizon, updates["to_horizon_id"])
            if not to_horizon:
                raise ValueError(f"Horizon {updates['to_horizon_id']} not found")

        target_from = updates.get("from_horizon_id", ladder.from_horizon_id)
        target_to = updates.get("to_horizon_id", ladder.to_horizon_id)
        if target_from == target_to:
            raise ValueError("from_horizon_id and to_horizon_id must be different")

        for key, value in updates.items():
            setattr(ladder, key, value)

        await db.commit()
        await db.refresh(ladder)
        return LadderResponse.model_validate(ladder)

    async def delete_ladder(self, db: AsyncSession, ladder_id: int) -> dict[str, Any]:
        """Удалить лестницу и все связанные с ней узлы."""
        ladder = await db.get(Ladder, ladder_id)
        if not ladder:
            raise ValueError(f"Ladder {ladder_id} not found")

        # Промежуточные узлы, связанные с лестницей через node_ladders (без horizon)
        inter_nodes = await db.execute(
            select(GraphNode.id)
            .join(node_ladders, node_ladders.c.node_id == GraphNode.id)
            .where(
                node_ladders.c.ladder_id == ladder_id,
                GraphNode.horizon_id.is_(None),
            ),
        )
        inter_node_ids = inter_nodes.scalars().all()

        # Конечные узлы (с horizon_id) – получаем объекты
        end_nodes_result = await db.execute(
            select(GraphNode).where(GraphNode.horizon_id.is_not(None)),
        )
        end_nodes = end_nodes_result.scalars().all()

        # Удаляем связи node_ladders и рёбра, связанные с лестницей
        await db.execute(
            delete(node_ladders).where(node_ladders.c.ladder_id == ladder_id),
        )

        # Удаляем вертикальные рёбра, связанные с этими узлами
        all_node_ids = list(inter_node_ids) + [node.id for node in end_nodes]
        await db.execute(
            delete(GraphEdge).where(
                GraphEdge.edge_type == "vertical",
                or_(
                    GraphEdge.from_node_id.in_(all_node_ids),
                    GraphEdge.to_node_id.in_(all_node_ids),
                ),
            ),
        )

        # Удаление промежуточных узлов
        if inter_node_ids:
            await db.execute(delete(GraphNode).where(GraphNode.id.in_(inter_node_ids)))

        # Обновляем тип конечных узлов (если они были лестницами)
        for node in end_nodes:
            if node.node_type == "ladder":
                node.node_type = "road"  # type: ignore[assignment]
            # Добавлять в сессию не нужно – node уже в ней

        # Удаление лестницы
        await db.delete(ladder)
        await db.commit()

        return {
            "status": "success",
            "message": "Ladder deleted successfully",
            "id": ladder_id,
            "deleted_nodes": inter_node_ids,
        }

    async def delete_ladder_node(
        self,
        db: AsyncSession,
        node_id: int,
    ) -> dict[str, Any]:
        """Удалить ladder узел и все связанные узлы на других уровнях"""
        node = await db.get(GraphNode, node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        if node.node_type != "ladder":
            raise ValueError(f"Node {node_id} is not a ladder type")

        linked_nodes = []
        if node.linked_nodes:
            try:
                linked_data = json.loads(str(node.linked_nodes))
                linked_nodes = list(linked_data.values())
            except Exception:  # noqa: S110
                pass

        nodes_to_delete = [node.id] + linked_nodes
        # Явно получаем все лестницы, связанные с этим узлом, до его удаления,
        # чтобы позже при необходимости удалить "осиротевшие" лестницы.
        ladders_result = await db.execute(
            select(Ladder)
            .join(node_ladders, node_ladders.c.ladder_id == Ladder.id)
            .where(node_ladders.c.node_id == node_id),
        )
        related_ladders = ladders_result.scalars().all()

        if nodes_to_delete:
            # Сначала чистим связи node_ladders, иначе FK не даст удалить graph_nodes
            await db.execute(
                delete(node_ladders).where(node_ladders.c.node_id.in_(nodes_to_delete)),
            )
            await db.execute(
                delete(GraphEdge).where(
                    or_(
                        GraphEdge.from_node_id.in_(nodes_to_delete),
                        GraphEdge.to_node_id.in_(nodes_to_delete),
                    ),
                ),
            )

            await db.execute(
                delete(GraphNode).where(GraphNode.id.in_(nodes_to_delete)),
            )
        # Удаляем лестницы, которые больше не связаны ни с одним узлом
        for ladder in related_ladders:
            # Проверяем, остались ли у лестницы связанные узлы, через явный запрос
            nodes_result = await db.execute(
                select(GraphNode.id)
                .join(node_ladders, node_ladders.c.node_id == GraphNode.id)
                .where(node_ladders.c.ladder_id == ladder.id),
            )
            remaining_nodes = nodes_result.scalars().all()
            if not remaining_nodes:
                await db.delete(ladder)

        await db.commit()

        # Уведомляем борт о каждом удалённом ladder-узле (данные пустые, борт сам очистит связи)
        for nid in nodes_to_delete:
            await event_publisher.publish_entity_changed(
                entity_type="ladder",
                entity_id=nid,
                action="delete",
                data={},
            )

        return {"message": "Ladder nodes deleted successfully", "deleted_nodes": nodes_to_delete}

    async def connect_ladder_nodes(
        self,
        db: AsyncSession,
        from_node_id: int,
        to_node_id: int,
    ) -> dict[str, Any]:
        """Создать лестницу между двумя конкретными узлами по их ID"""
        from_node = await db.get(GraphNode, from_node_id)
        if not from_node:
            raise ValueError(f"Source node {from_node_id} not found")

        to_node = await db.get(GraphNode, to_node_id)
        if not to_node:
            raise ValueError(f"Target node {to_node_id} not found")

        if from_node.horizon_id == to_node.horizon_id:
            raise ValueError("Nodes must be on different levels")

        existing_edge_result = await db.execute(
            select(GraphEdge).where(
                or_(
                    and_(
                        GraphEdge.from_node_id == from_node_id,
                        GraphEdge.to_node_id == to_node_id,
                    ),
                    and_(
                        GraphEdge.from_node_id == to_node_id,
                        GraphEdge.to_node_id == from_node_id,
                    ),
                ),
            ),
        )
        existing_edge = existing_edge_result.scalar_one_or_none()

        if existing_edge is not None:
            raise ValueError("Edge already exists between these nodes")

        # Создаём сущность Ladder в рамках текущей транзакции
        ladder = Ladder(
            from_horizon_id=from_node.horizon_id,
            to_horizon_id=to_node.horizon_id,
            is_active=False,
            is_completed=False,
        )
        db.add(ladder)
        await db.flush()

        if from_node.node_type != "ladder":
            from_node.node_type = "ladder"  # type: ignore[assignment]
        if to_node.node_type != "ladder":
            to_node.node_type = "ladder"  # type: ignore[assignment]

        # В async-ORM нельзя полагаться на ленивую загрузку коллекций отношений:
        # append() может спровоцировать lazy-load и привести к MissingGreenlet.
        # Поэтому связываем узлы с лестницей явными INSERT-ами в таблицу связи.
        await db.execute(
            insert(node_ladders).values(node_id=from_node_id, ladder_id=ladder.id),
        )
        await db.execute(
            insert(node_ladders).values(node_id=to_node_id, ladder_id=ladder.id),
        )

        from_linked = {}
        if from_node.linked_nodes:
            try:
                from_linked = json.loads(str(from_node.linked_nodes))
            except Exception:  # noqa: S110
                pass
        from_linked[str(to_node.horizon_id)] = to_node.id
        from_node.linked_nodes = json.dumps(from_linked)  # type: ignore[assignment]

        to_linked = {}
        if to_node.linked_nodes:
            try:
                to_linked = json.loads(str(to_node.linked_nodes))
            except Exception:  # noqa: S110
                pass

        to_linked[str(from_node.horizon_id)] = from_node.id
        to_node.linked_nodes = json.dumps(to_linked)  # type: ignore[assignment]

        ladder_edge = GraphEdge(
            horizon_id=None,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            edge_type="vertical",
            direction=RoadDirectionEnum.bidirectional.value,
            geometry=func.ST_MakeLine(from_node.geometry, to_node.geometry),
        )
        db.add(ladder_edge)
        await db.flush()

        await db.commit()

        await db.refresh(ladder_edge)

        # Для ответа нужны x/y, которые вычисляются из geometry (ST_X/ST_Y),
        # поэтому формируем NodeResponse так же, как это делает nodes-сервис.
        from_node = await node_service.get_node_by_id(db, from_node_id)  # type: ignore[assignment]
        to_node = await node_service.get_node_by_id(db, to_node_id)  # type: ignore[assignment]
        if not from_node or not to_node:
            raise ValueError("Failed to load horizon data for ladder nodes")

        from_horizon = await db.get(Horizon, from_node.horizon_id)
        to_horizon = await db.get(Horizon, to_node.horizon_id)
        if not from_horizon or not to_horizon:
            raise ValueError("Failed to load horizon data for ladder nodes")

        # Публикуем ladder-событие (данные пустые, борт сам подтянет GET-ами)
        await event_publisher.publish_entity_changed(
            entity_type="ladder",
            entity_id=ladder.id,
            action="create",
            data={},
        )

        return {
            "message": "Ladder created successfully",
            "ladder_id": ladder.id,
            "from_node": from_node.model_dump(),  # type: ignore[attr-defined]
            "to_node": to_node.model_dump(),  # type: ignore[attr-defined]
            "ladder_edge": EdgeResponse.model_validate(ladder_edge).model_dump(),
            "from_horizon": {
                "id": from_horizon.id,
                "name": from_horizon.name,
                "height": from_horizon.height,
            },
            "to_horizon": {
                "id": to_horizon.id,
                "name": to_horizon.name,
                "height": to_horizon.height,
            },
        }


# Глобальный экземпляр сервиса
ladder_service = LadderService()
