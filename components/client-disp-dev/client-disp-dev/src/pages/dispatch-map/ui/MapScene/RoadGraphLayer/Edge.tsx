import { Line } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { Line2 } from 'three-stdlib';

import { MAP_SCENE } from '../../../config/map-scene';
import { useDragCoordinationContext } from '../../../lib/drawing';
import type { GraphNode } from '../../../model/graph';

/** Свойства компонента {@link Edge}. */
interface EdgeProps {
  /** Начальный узел ребра. */
  readonly from: GraphNode;
  /** Конечный узел ребра. */
  readonly to: GraphNode;
  /** Цвет ребра. По умолчанию — {@link MAP_SCENE.ROAD_GRAPH.EDGE_COLOR}. */
  readonly color?: string;
}

/**
 * Линия между двумя узлами дорожного графа.
 *
 * При перетаскивании узла геометрия линии обновляется напрямую через `useFrame`,
 * минуя React-рендер, чтобы визуально следовать за курсором без задержек.
 */
export function Edge({ from, to, color = MAP_SCENE.ROAD_GRAPH.EDGE_COLOR }: EdgeProps) {
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
    <Line
      ref={lineRef}
      points={[
        [from.x, MAP_SCENE.ROAD_GRAPH_Y, from.z],
        [to.x, MAP_SCENE.ROAD_GRAPH_Y, to.z],
      ]}
      color={color}
      lineWidth={MAP_SCENE.ROAD_GRAPH.EDGE_WIDTH}
      transparent
      depthTest={false}
      renderOrder={MAP_SCENE.ROAD_GRAPH_Y}
    />
  );
}
