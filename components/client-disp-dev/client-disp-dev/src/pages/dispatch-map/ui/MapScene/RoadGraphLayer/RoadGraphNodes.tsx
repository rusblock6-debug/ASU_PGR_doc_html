import { useState } from 'react';

import { MAP_SCENE } from '../../../config/map-scene';
import { type MoveScenePoint, CirclePoint, useDragCoordinationContext } from '../../../lib/drawing';
import type { GraphNode } from '../../../model/graph';

import { NodeTooltip } from './NodeTooltip';

/**
 * Представляет свойства компонента {@link RoadGraphNodes}.
 */
interface RoadGraphNodesProps {
  /** Узлы графа. */
  readonly nodes: readonly GraphNode[];
  /** Перемещает узел по плоскости. */
  readonly moveNode: MoveScenePoint;
  /** Удаляет узел по tempId. */
  readonly removeNode: (tempId: string) => void;
  /** tempId узла, от которого рисуется ребро. null — нет активного рисования. */
  readonly drawingFromNodeId: string | null;
  /** Добавляет ребро между двумя узлами. */
  readonly addEdge: (fromId: string, toId: string) => void;
  /** Начинает рисование ребра от указанного узла. */
  readonly startDrawingFrom: (nodeId: string) => void;
  /** Отменяет рисование ребра. */
  readonly cancelDrawing: () => void;
  /** Цвет вершины. По умолчанию — {@link MAP_SCENE.ROAD_GRAPH.NODE_COLOR}. */
  readonly color?: string;
}

/**
 * Узлы дорожного графа с тултипами.
 */
export function RoadGraphNodes({
  nodes,
  moveNode,
  removeNode,
  drawingFromNodeId,
  addEdge,
  startDrawingFrom,
  cancelDrawing,
  color = MAP_SCENE.ROAD_GRAPH.NODE_COLOR,
}: RoadGraphNodesProps) {
  const { isDragging } = useDragCoordinationContext();

  const [activeTooltipNodeId, setActiveTooltipNodeId] = useState<string | null>(null);

  const handleDragStateChange = (dragging: boolean) => {
    if (dragging) setActiveTooltipNodeId(null);
  };

  const handleNodeHover = (id: string, hovered: boolean) => {
    if (hovered && !isDragging()) {
      setActiveTooltipNodeId(id);
    }
  };

  const handleNodeClick = (id: string) => {
    if (drawingFromNodeId) {
      addEdge(drawingFromNodeId, id);
      cancelDrawing();
    }
  };

  const handleNodeDelete = (id: string) => {
    removeNode(id);
    setActiveTooltipNodeId(null);
  };

  const handleStartDrawingFrom = (id: string) => {
    startDrawingFrom(id);
    setActiveTooltipNodeId(null);
  };

  const handleToggleDrawing = (nodeId: string) => {
    if (drawingFromNodeId === nodeId) {
      cancelDrawing();
    } else {
      handleStartDrawingFrom(nodeId);
    }
  };

  return nodes.map((node) => {
    const isDrawingSource = drawingFromNodeId === node.tempId;

    return (
      <group key={node.tempId}>
        <CirclePoint
          deferMove
          id={node.tempId}
          x={node.x}
          z={node.z}
          y={MAP_SCENE.ROAD_GRAPH_Y + MAP_SCENE.POINT_ABOVE_LAYER_Y}
          size={MAP_SCENE.ROAD_GRAPH.NODE_SIZE}
          color={color}
          borderColor={MAP_SCENE.ROAD_GRAPH.NODE_BORDER_COLOR}
          hoverColor={MAP_SCENE.ROAD_GRAPH.NODE_HOVER_BORDER_COLOR}
          onMove={moveNode}
          onClick={handleNodeClick}
          onHoverChange={handleNodeHover}
          onDoubleClick={handleNodeDelete}
          onDragStateChange={handleDragStateChange}
        />
        {activeTooltipNodeId === node.tempId && (
          <NodeTooltip
            position={[node.x, MAP_SCENE.ROAD_GRAPH_Y, node.z]}
            isDrawingSource={isDrawingSource}
            onAddEdge={() => handleToggleDrawing(node.tempId)}
            onDelete={() => handleNodeDelete(node.tempId)}
            onClose={() => setActiveTooltipNodeId(null)}
          />
        )}
      </group>
    );
  });
}
