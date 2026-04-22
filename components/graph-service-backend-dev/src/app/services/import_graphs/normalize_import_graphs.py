"""Сервис для нормализации графов из внешних источников"""

import logging
import random
from typing import Any

from app.schemas.import_graphs import (
    ImportEdge,
    ImportGraphData,
    ImportHorizon,
    ImportNode,
    ImportTag,
)

logger = logging.getLogger(__name__)


class NormalizeImportGraphs:
    """Класс для нормализации графов из внешних источников"""

    def normalize_graph_data(
        self,
        data: dict[str, Any],
    ) -> ImportGraphData:
        """Нормализовать данные графа из различных форматов

        Args:
            data: Сырые данные графа

        Returns:
            ImportGraphData
        """
        # Проверяем формат данных
        if "levels" in data:
            return self._normalize_structured_levels(data)
        elif "type" in data and data["type"] == "FeatureCollection":
            return self._normalize_geojson(data)
        else:
            return self._normalize_flat_graph(data)

    @staticmethod
    def _normalize_structured_levels(
        data: dict[str, Any],
    ) -> ImportGraphData:
        """Нормализация формата с явной структурой уровней"""
        horizons = []

        for level_data in data.get("levels", []):
            nodes = [ImportNode(**node) for node in level_data.get("nodes", [])]
            edges = [ImportEdge(**edge) for edge in level_data.get("edges", [])]
            tags = [ImportTag(**tag) for tag in level_data.get("tags", [])]

            horizons.append(
                ImportHorizon(
                    id=level_data.get("id"),
                    name=level_data.get("name", f"Level {level_data.get('height', 0)}"),
                    height=level_data.get("height", 0.0),
                    description=level_data.get("description"),
                    nodes=nodes,
                    edges=edges,
                    tags=tags,
                ),
            )

        return ImportGraphData(horizons=horizons)

    @staticmethod
    def _normalize_flat_graph(
        data: dict[str, Any],
    ) -> ImportGraphData:
        """Нормализация плоского формата графа"""
        nodes = [ImportNode(**node) for node in data.get("nodes", [])]
        edges = [ImportEdge(**edge) for edge in data.get("edges", [])]
        tags = [ImportTag(**tag) for tag in data.get("tags", [])]

        height_groups: dict[float, list[ImportNode]] = {}
        for node in nodes:
            height = node.z or 0.0
            if height not in height_groups:
                height_groups[height] = []
            height_groups[height].append(node)

        horizons = []
        for height, level_nodes in height_groups.items():
            level_edges = [
                e
                for e in edges
                if any(n.id == e.from_node for n in level_nodes)
                or any(n.id == e.to_node for n in level_nodes)
            ]
            level_tags = [
                t for t in tags if any(abs((n.z or 0.0) - (t.z or 0.0)) < 0.1 for n in level_nodes)
            ]

            horizons.append(
                ImportHorizon(
                    id=None,
                    name=f"Level {height}",
                    height=height,
                    description=None,
                    nodes=level_nodes,
                    edges=level_edges,
                    tags=level_tags,
                ),
            )

        return ImportGraphData(horizons=horizons)

    @staticmethod
    def _normalize_geojson(
        data: dict[str, Any],
    ) -> ImportGraphData:
        """Нормализация GeoJSON формата"""
        nodes: dict[tuple, ImportNode] = {}
        edges: list[ImportEdge] = []
        tags: list[ImportTag] = []

        def get_or_create_node(coord: list, default_name_prefix: str = "Node") -> ImportNode:
            """Создает или возвращает узел по координате.
            Используем координату как ключ, чтобы для одинаковых точек не плодить узлы.
            """
            x = coord[0]
            y = coord[1]
            z = coord[2] if len(coord) > 2 else 0.0
            key = (x, y, z)

            if key not in nodes:
                node_id = len(nodes) + 1
                node = ImportNode(
                    id=node_id,
                    x=x,
                    y=y,
                    z=z,
                    node_type="road",
                )
                nodes[key] = node

            return nodes[key]

        for feature in data.get("features", []):
            geom = feature.get("geometry", {})
            props = feature.get("properties", {})

            if geom.get("type") == "Point":
                coords = geom.get("coordinates", [])
                node = ImportNode(
                    id=props.get("id", random.randint(1000, 9999)),  # noqa: S311
                    x=coords[0],
                    y=coords[1],
                    z=coords[2] if len(coords) > 2 else 0.0,
                    node_type=props.get("type", "road"),
                )
                nodes[(node.x, node.y, node.z)] = node

            elif geom.get("type") == "LineString":
                coords = geom.get("coordinates", [])
                if len(coords) >= 2:
                    from_node = get_or_create_node(coords[0], default_name_prefix="LineStart")
                    to_node = get_or_create_node(coords[-1], default_name_prefix="LineEnd")

                    from_id = props.get("from", from_node.id)
                    to_id = props.get("to", to_node.id)

                    edges.append(
                        ImportEdge.model_validate({"from": from_id, "to": to_id}),
                    )

        height_groups: dict[float, list[ImportNode]] = {}
        for node in nodes.values():
            height = node.z or 0.0
            if height not in height_groups:
                height_groups[height] = []
            height_groups[height].append(node)

        horizons = []
        for height, level_nodes in height_groups.items():
            level_edges = [
                e
                for e in edges
                if any(n.id == e.from_node for n in level_nodes)
                or any(n.id == e.to_node for n in level_nodes)
            ]
            level_tags = [
                t for t in tags if any(abs((n.z or 0.0) - (t.z or 0.0)) < 0.1 for n in level_nodes)
            ]

            horizons.append(
                ImportHorizon(
                    id=None,
                    name=f"Level {height}",
                    height=height,
                    description=None,
                    nodes=level_nodes,
                    edges=level_edges,
                    tags=level_tags,
                ),
            )

        return ImportGraphData(horizons=horizons)


normalize_import_graph = NormalizeImportGraphs()
