"""Сервис для импорта графов из внешних источников"""

import logging
from typing import Any

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enum.edges import RoadDirectionEnum
from app.enum.places import PlaceTypeEnum
from app.models.database import GraphEdge, GraphNode, Horizon, Place, Tag
from app.schemas.import_graphs import (
    ImportGraphData,
    ImportGraphRequest,
    ImportHorizon,
    ImportResultResponse,
)
from app.services.import_graphs.normalize_import_graphs import normalize_import_graph
from config.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class ImportGraphService:
    """Сервис для импорта графов из внешних источников"""

    def __init__(self):
        self.node_id_mapping: dict[Any, int] = {}  # Внешний ID → БД ID

    async def import_graph_from_request(
        self,
        import_request: ImportGraphRequest,
    ) -> ImportResultResponse:
        """Обработать запрос импорта графа и вернуть результат."""
        if import_request.source_url:
            raw_data = await self.fetch_graph_from_url(import_request.source_url)
        elif import_request.source_data:
            raw_data = import_request.source_data
        else:
            raise ValueError("Either source_url or source_data must be provided")

        logger.info(
            "Import request params: create_nodes_with_tags=%s,"
            " tag_radius=%s, horizon_id=%s, overwrite_existing=%s",
            import_request.create_nodes_with_tags,
            import_request.tag_radius,
            import_request.horizon_id,
            import_request.overwrite_existing,
        )

        graph_data = normalize_import_graph.normalize_graph_data(raw_data)
        # Если после нормализации нет уровней, возвращаем внятную ошибку,
        # чтобы не получать "успех" с нулевыми объектами
        if not graph_data.horizons:
            raise ValueError(
                "В переданных данных не найдено ни одного горизонта. "
                "Убедитесь, что используете один из поддерживаемых форматов: "
                "levels[], nodes/edges/tags или GeoJSON FeatureCollection.",
            )

        result = await self.import_graph(
            graph_data=graph_data,
            overwrite_existing=import_request.overwrite_existing,
            target_horizon_id=import_request.horizon_id,
            create_nodes_with_tags=import_request.create_nodes_with_tags,
            tag_radius=import_request.tag_radius,
        )

        return result

    @staticmethod
    async def fetch_graph_from_url(url: str) -> dict[str, Any]:
        """Загрузить граф из внешнего API

        Args:
            url: URL для загрузки графа

        Returns:
            Dict с данными графа
        """
        try:
            logger.info(f"Fetching graph from URL: {url}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                data = response.json()
                logger.info(f"Successfully fetched graph data from {url}")
                return data

        except httpx.RequestError as e:
            logger.error(f"Failed to fetch graph from URL {url}: {e}")
            raise ValueError(f"Failed to fetch graph from URL: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error parsing graph data from URL {url}: {e}")
            raise ValueError(f"Error parsing graph data: {str(e)}") from e

    async def import_graph(
        self,
        graph_data: ImportGraphData,
        overwrite_existing: bool = False,
        target_horizon_id: int | None = None,
        create_nodes_with_tags: bool = True,
        tag_radius: float = 10.0,
    ) -> ImportResultResponse:
        """Импортировать граф в базу данных"""
        result = ImportResultResponse(
            success=False,
            message="Import not started",
            created_horizons=0,
            created_nodes=0,
            created_edges=0,
            created_tags=0,
        )

        try:
            async with AsyncSessionLocal() as db:
                self.node_id_mapping.clear()

                # Если указан target_horizon_id, импортируем в существующий уровень
                if target_horizon_id:
                    level_result = await db.execute(
                        select(Horizon).where(Horizon.id == target_horizon_id),
                    )
                    level = level_result.scalar_one_or_none()
                    if not level:
                        result.message = f"Target level {target_horizon_id} not found"
                        result.errors.append(result.message)
                        return result

                    # ✅ ВАЖНО: Очищаем существующие данные уровня перед импортом
                    # чтобы избежать конфликтов с point_id, node_id и edge_id
                    logger.info(f"Clearing existing data from level {level.id} before import")
                    await self._clear_level_data(db, level)

                    # Импортируем все данные в этот уровень
                    for horizon_data in graph_data.horizons:
                        await self._import_level_data(db, level, horizon_data, result)

                    result.horizon_ids.append(level.id)  # type: ignore[arg-type]
                    result.created_horizons = 0  # Не создавали новых
                else:
                    # Создаём новые уровни
                    for horizon_data in graph_data.horizons:
                        # Проверяем существование уровня по высоте
                        existing_level_result = await db.execute(
                            select(Horizon).where(Horizon.height == horizon_data.height),
                        )
                        existing_level = existing_level_result.scalar_one_or_none()

                        if existing_level and not overwrite_existing:
                            logger.warning(
                                f"Horizon with height {horizon_data.height}"
                                " already exists, skipping",
                            )
                            result.errors.append(
                                f"Horizon at height {horizon_data.height} already exists",
                            )
                            continue

                        if existing_level and overwrite_existing:
                            # Удаляем старые данные
                            await self._clear_level_data(db, existing_level)
                            level = existing_level
                        else:
                            # Создаём новый уровень
                            level = Horizon(
                                name=horizon_data.name,
                                height=horizon_data.height,
                            )
                            db.add(level)
                            await db.flush()
                            result.created_horizons += 1

                        # Импортируем данные уровня
                        await self._import_level_data(db, level, horizon_data, result)
                        result.horizon_ids.append(level.id)  # type: ignore[arg-type]

                await db.commit()

                # Если ничего не создано — сигнализируем как ошибку, чтобы не терять проблему
                if (
                    result.created_horizons == 0
                    and result.created_nodes == 0
                    and result.created_edges == 0
                    and result.created_tags == 0
                ):
                    result.message = (
                        "Import finished, но данные не были добавлены. "
                        "Проверьте структуру входных данных"
                        " и параметры overwrite_existing/horizon_id."
                    )
                    result.errors.append(result.message)
                    logger.warning(result.message)
                else:
                    result.success = True
                    result.message = (
                        f"Successfully imported {result.created_horizons} horizons, "
                        f"{result.created_nodes} nodes, {result.created_edges} edges,"
                        f" {result.created_tags} tags"
                    )
                    logger.info(result.message)

        except Exception as e:
            logger.error(f"Error importing graph: {e}")
            import traceback

            logger.error(traceback.format_exc())
            result.success = False
            result.message = f"Import failed: {str(e)}"
            result.errors.append(str(e))

        return result

    async def _import_level_data(
        self,
        db: AsyncSession,
        level: Horizon,
        level_data: ImportHorizon,
        result: ImportResultResponse,
    ):
        """Импортировать данные одного уровня"""
        # Импорт узлов
        for node_data in level_data.nodes:
            try:
                node = GraphNode(
                    horizon_id=level.id,
                    node_type=node_data.node_type,
                    geometry=func.ST_SetSRID(
                        func.ST_MakePoint(
                            float(node_data.x),
                            float(node_data.y),
                            float(node_data.z) if node_data.z is not None else level.height,
                        ),
                        4326,
                    ),
                )
                db.add(node)
                await db.flush()

                # Сохраняем маппинг внешнего ID → БД ID
                self.node_id_mapping[node_data.id] = node.id  # type: ignore[assignment]
                result.created_nodes += 1
            except Exception as e:
                logger.error(f"Error creating node {node_data.id}: {e}")
                result.errors.append(f"Node {node_data.id}: {str(e)}")

        # Импорт рёбер
        for edge_data in level_data.edges:
            try:
                from_node_id = self.node_id_mapping.get(edge_data.from_node)
                to_node_id = self.node_id_mapping.get(edge_data.to_node)

                if from_node_id is None:
                    logger.warning(
                        f"From node {edge_data.from_node} not found in mapping, skipping edge",
                    )
                    continue
                if to_node_id is None:
                    logger.warning(
                        f"To node {edge_data.to_node} not found in mapping, skipping edge",
                    )
                    continue

                # Получаем узлы для создания геометрии (db.get() уже async)
                from_node = await db.get(GraphNode, from_node_id)
                to_node = await db.get(GraphNode, to_node_id)

                if not from_node or not to_node:
                    logger.warning("Nodes not found in DB for edge, skipping")
                    continue

                edge = GraphEdge(
                    horizon_id=level.id,
                    from_node_id=from_node_id,
                    to_node_id=to_node_id,
                    edge_type=edge_data.edge_type if hasattr(edge_data, "edge_type") else "road",
                    direction=edge_data.direction
                    if hasattr(edge_data, "direction")
                    else RoadDirectionEnum.bidirectional.value,
                    geometry=func.ST_MakeLine(from_node.geometry, to_node.geometry),
                )
                db.add(edge)
                result.created_edges += 1
            except Exception as e:
                logger.error(f"Error creating edge {edge_data.from_node}->{edge_data.to_node}: {e}")
                result.errors.append(f"Edge {edge_data.from_node}->{edge_data.to_node}: {str(e)}")

        # Импорт меток
        for tag_data in level_data.tags:
            try:
                # Генерируем уникальный point_id используя реальный ID узла из БД
                original_point_id = tag_data.point_id or f"tag_{tag_data.id}"

                # Если point_id в формате "node_{external_id}", заменяем на реальный DB ID
                if original_point_id.startswith("node_"):
                    try:
                        external_node_id = int(original_point_id.replace("node_", ""))
                        db_node_id = self.node_id_mapping.get(external_node_id)
                        if db_node_id:
                            unique_point_id = f"node_{db_node_id}"
                        else:
                            unique_point_id = original_point_id
                    except ValueError:
                        unique_point_id = original_point_id
                else:
                    unique_point_id = original_point_id

                # Конвертируем Canvas координаты в GPS для хранения в Place
                from app.services.places import coords_to_geometry
                from app.utils.coordinates import transform_canvas_to_gps

                # tag_data.x и tag_data.y - это Canvas координаты
                # Конвертируем их в GPS для хранения
                gps_lat, gps_lon = transform_canvas_to_gps(tag_data.x, tag_data.y)

                # Создаем GraphNode для места: geometry хранится на узле.
                node = GraphNode(
                    horizon_id=level.id,
                    node_type="road",
                )
                node.geometry = coords_to_geometry(gps_lon, gps_lat, float(level.height))  # type: ignore[assignment]
                db.add(node)
                await db.flush()  # Получаем ID node

                # Создаем Place и связываем с node_id
                place = Place(
                    name=tag_data.name or f"Tag {unique_point_id}",
                    type=PlaceTypeEnum.load,
                    node_id=node.id,
                )
                db.add(place)
                await db.flush()  # Получаем ID place

                # Генерируем правильный MAC адрес
                import hashlib

                mac_hash = hashlib.md5(
                    unique_point_id.encode(),
                    usedforsecurity=False,
                ).hexdigest()[:12]
                tag_mac = ":".join([mac_hash[i : i + 2] for i in range(0, 12, 2)])

                # Создаем Tag и связываем с Place
                tag = Tag(
                    place_id=place.id,
                    tag_name=unique_point_id,
                    tag_mac=tag_mac,
                    radius=tag_data.radius,
                )
                db.add(tag)
                result.created_tags += 1
            except Exception as e:
                logger.error(f"Error creating tag {tag_data.point_id}: {e}")
                result.errors.append(f"Tag {tag_data.point_id}: {str(e)}")

    async def _clear_level_data(self, db: AsyncSession, level: Horizon):
        """Очистить данные уровня: только узлы и рёбра. Места и теги не удаляем."""
        logger.info(
            f"Clearing nodes and edges for level {level.id} (places and tags are preserved)",
        )

        # 1. Получаем все ID узлов этого уровня
        node_ids_result = await db.execute(
            select(GraphNode.id).where(GraphNode.horizon_id == level.id),
        )
        node_ids = [nid for nid in node_ids_result.scalars().all()]
        logger.info(f"Found {len(node_ids)} nodes in level {level.id}")

        if node_ids:
            # 2. Удаляем ВСЕ рёбра, которые ссылаются на узлы этого уровня
            # (независимо от horizon_id ребра, так как узлы могут быть связаны с другими уровнями)
            edges_result = await db.execute(
                delete(GraphEdge).where(
                    (GraphEdge.from_node_id.in_(node_ids)) | (GraphEdge.to_node_id.in_(node_ids)),
                ),
            )
            edges_deleted = edges_result.rowcount  # type: ignore[attr-defined]
            logger.info(f"Deleted {edges_deleted} edges referencing nodes from level {level.id}")

            # 3. Теперь безопасно удаляем узлы
            nodes_result = await db.execute(
                delete(GraphNode).where(GraphNode.horizon_id == level.id),
            )
            nodes_deleted = nodes_result.rowcount  # type: ignore[attr-defined]
            logger.info(f"Deleted {nodes_deleted} nodes from level {level.id}")

        # Фиксируем изменения
        await db.flush()
        logger.info(f"Successfully cleared all data for level {level.id}")


# Глобальный экземпляр сервиса
import_graph_service = ImportGraphService()
