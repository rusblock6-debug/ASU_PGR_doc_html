import { Line } from '@react-three/drei';
import type { Ref } from 'react';
import type { Line2 } from 'three-stdlib';

import { MAP_SCENE } from '../../../config/map-scene';
import type { ScenePoint } from '../../../lib/drawing';

/** Свойства компонента {@link Edge}. */
interface EdgeProps {
  readonly ref?: Ref<Line2>;
  /** Начальная точка ребра. */
  readonly from: ScenePoint;
  /** Конечная точка ребра. */
  readonly to: ScenePoint;
  /** Цвет ребра. По умолчанию — {@link MAP_SCENE.ROAD_GRAPH.EDGE_COLOR}. */
  readonly color?: string;
  /** Толщина линии. По умолчанию — {@link MAP_SCENE.ROAD_GRAPH.EDGE_WIDTH}. */
  readonly lineWidth?: number;
  /** Рендерить линию пунктиром. */
  readonly dashed?: boolean;
  /** Длина штриха для пунктирной линии. */
  readonly dashSize?: number;
  /** Размер промежутка для пунктирной линии. */
  readonly gapSize?: number;
}

/**
 * Линия между двумя вершинами дорожного графа.
 */
export function Edge({
  ref,
  from,
  to,
  color = MAP_SCENE.ROAD_GRAPH.EDGE_COLOR,
  lineWidth = MAP_SCENE.ROAD_GRAPH.EDGE_WIDTH,
  dashed = false,
  dashSize,
  gapSize,
}: EdgeProps) {
  return (
    <Line
      ref={ref}
      points={[
        [from.x, MAP_SCENE.ROAD_GRAPH_Y, from.z],
        [to.x, MAP_SCENE.ROAD_GRAPH_Y, to.z],
      ]}
      color={color}
      lineWidth={lineWidth}
      dashed={dashed}
      dashSize={dashSize}
      gapSize={gapSize}
      transparent
      depthTest={false}
      renderOrder={MAP_SCENE.ROAD_GRAPH_Y}
    />
  );
}
