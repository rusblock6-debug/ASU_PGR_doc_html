import { Line } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { Line2 } from 'three-stdlib';

import { MAP_SCENE } from '../../../config/map-scene';
import type { GraphNode } from '../../../model/graph';
import { useGroundPointerContext } from '../../GroundPointerProvider';

/**
 * Представляет свойства компонента {@link PreviewEdge}.
 */
interface PreviewEdgeProps {
  /** tempId узла, от которого рисуется ребро. null — нет активного рисования. */
  readonly drawingFromNodeId: string | null;
  /** Карта узлов по tempId. */
  readonly nodesMap: ReadonlyMap<string, GraphNode>;
  /** Цвет ребра. По умолчанию — {@link MAP_SCENE.ROAD_GRAPH.EDGE_COLOR}. */
  readonly color?: string;
}

/**
 * Пунктирная линия от выбранного узла к текущей позиции курсора.
 *
 * Видима только когда активен режим рисования ребра (`drawingFromNodeId !== null`).
 * Позиция обновляется каждый кадр через `useFrame`.
 */
export function PreviewEdge({
  drawingFromNodeId,
  nodesMap,
  color = MAP_SCENE.ROAD_GRAPH.EDGE_COLOR,
}: PreviewEdgeProps) {
  const { pointerRef } = useGroundPointerContext();
  const lineRef = useRef<Line2>(null);

  useFrame(() => {
    const line = lineRef.current;
    if (!line) return;

    const fromNode = drawingFromNodeId ? nodesMap.get(drawingFromNodeId) : null;

    if (fromNode) {
      const { x, z } = pointerRef.current;
      line.geometry.setPositions([fromNode.x, MAP_SCENE.ROAD_GRAPH_Y, fromNode.z, x, MAP_SCENE.ROAD_GRAPH_Y, z]);
      line.computeLineDistances();
      line.visible = true;
    } else {
      line.visible = false;
    }
  });

  return (
    <Line
      ref={lineRef}
      points={[
        [0, MAP_SCENE.ROAD_GRAPH_Y, 0],
        [0, MAP_SCENE.ROAD_GRAPH_Y, 1],
      ]}
      color={color}
      lineWidth={7}
      dashed
      dashSize={8}
      gapSize={4}
      depthTest={false}
      renderOrder={MAP_SCENE.ROAD_GRAPH_Y}
    />
  );
}
