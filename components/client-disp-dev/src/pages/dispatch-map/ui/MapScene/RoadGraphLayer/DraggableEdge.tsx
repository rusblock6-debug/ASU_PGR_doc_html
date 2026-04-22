import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { Line2 } from 'three-stdlib';

import { MAP_SCENE } from '../../../config/map-scene';
import { useDragCoordinationContext } from '../../../lib/drawing';
import type { GraphNode } from '../../../model/graph';

import { Edge } from './Edge';

/** Свойства компонента {@link DraggableEdge}. */
interface DraggableEdgeProps {
  /** Начальный узел ребра. */
  readonly from: GraphNode;
  /** Конечный узел ребра. */
  readonly to: GraphNode;
  /** Цвет ребра. По умолчанию — {@link MAP_SCENE.ROAD_GRAPH.EDGE_COLOR}. */
  readonly color?: string;
}

/**
 * Линия между двумя узлами дорожного графа с поддержкой перетаскивания.
 *
 * При перетаскивании узла геометрия линии обновляется напрямую через `useFrame`,
 * минуя React-рендер, чтобы визуально следовать за курсором без задержек.
 */
export function DraggableEdge({ from, to, color }: DraggableEdgeProps) {
  const { dragPositionRef } = useDragCoordinationContext();
  const lineRef = useRef<Line2>(null);

  useFrame(() => {
    const dragPosition = dragPositionRef.current;
    if (!dragPosition || !lineRef.current) return;

    const isFromDragged = dragPosition.id === from.tempId;
    const isToDragged = dragPosition.id === to.tempId;
    if (!isFromDragged && !isToDragged) return;

    const fromPoint = isFromDragged ? dragPosition : from;
    const toPoint = isToDragged ? dragPosition : to;
    const y = MAP_SCENE.ROAD_GRAPH_Y;

    lineRef.current.geometry.setPositions([fromPoint.x, y, fromPoint.z, toPoint.x, y, toPoint.z]);
  });

  return (
    <Edge
      ref={lineRef}
      from={from}
      to={to}
      color={color}
    />
  );
}
