import { useState } from 'react';

import { EMPTY_ARRAY } from '@/shared/lib/constants';

import { MAP_SCENE } from '../../../config/map-scene';
import {
  calculateCumulativeDistances,
  formatDistance,
  type MoveScenePoint,
  CirclePoint,
  type PolylinePoint,
} from '../../../lib/drawing';

import { RulerPointTooltip } from './RulerPointTooltip';

/** Цвет вершин линейки. */
const POINT_COLOR = '#FEFCF9';

/**
 * Представляет свойства компонента {@link RulerPoints}.
 */
interface RulerPointsProps {
  /** Точки полилинии. */
  readonly points: readonly PolylinePoint[];
  /** Перемещает точку по плоскости. */
  readonly movePoint: MoveScenePoint;
  /** Удаляет точку по ID. */
  readonly removePoint: (id: string) => void;
}

/**
 * Вершины линейки с тултипами.
 */
export function RulerPoints({ points, movePoint, removePoint }: RulerPointsProps) {
  const [activeTooltipPointId, setActiveTooltipPointId] = useState<string | null>(null);
  const distances = points.length >= 2 ? calculateCumulativeDistances(points) : EMPTY_ARRAY;

  const handlePointHover = (id: string, hovered: boolean) => {
    if (hovered) {
      setActiveTooltipPointId(id);
    }
  };

  const handlePointDelete = (id: string) => {
    removePoint(id);
    setActiveTooltipPointId(null);
  };

  return points.map((point, index) => (
    <group key={point.id}>
      <CirclePoint
        id={point.id}
        x={point.x}
        z={point.z}
        y={MAP_SCENE.RULER_Y + MAP_SCENE.POINT_ABOVE_LAYER_Y}
        size={4}
        color={POINT_COLOR}
        onMove={movePoint}
        onHoverChange={handlePointHover}
        onDoubleClick={handlePointDelete}
      />
      {activeTooltipPointId === point.id && (
        <RulerPointTooltip
          position={[point.x, MAP_SCENE.RULER_Y, point.z]}
          distance={index > 0 && index < distances.length ? formatDistance(distances[index]) : null}
          onDelete={() => handlePointDelete(point.id)}
          onClose={() => setActiveTooltipPointId(null)}
        />
      )}
    </group>
  ));
}
