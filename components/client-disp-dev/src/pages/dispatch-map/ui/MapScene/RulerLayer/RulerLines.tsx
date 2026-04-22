import { Line } from '@react-three/drei';
import type { Vector3Tuple } from 'three';

import { MAP_SCENE } from '../../../config/map-scene';
import type { ScenePoint } from '../../../lib/drawing';

/** Цвет линии линейки. */
const LINE_COLOR = '#FEFCF9';

/** Толщина линии линейки в px. */
const LINE_WIDTH = 4;

/** Цвет обводки линии линейки. */
const BORDER_LINE_COLOR = '#D15C29';

/** Толщина обводки линии в px. */
const BORDER_WIDTH = 2;

/**
 * Представляет свойства компонента {@link RulerLines}.
 */
interface RulerLinesProps {
  /** Точки полилинии. */
  readonly points: readonly ScenePoint[];
}

/**
 * Линия линейки с обводкой.
 *
 * Отрисовывает две линии: широкую обводку и основную линию поверх неё.
 */
export function RulerLines({ points }: RulerLinesProps) {
  const linePoints = points.map((point): Vector3Tuple => [point.x, MAP_SCENE.RULER_Y, point.z]);

  return (
    <>
      <Line
        points={linePoints}
        color={BORDER_LINE_COLOR}
        lineWidth={LINE_WIDTH + BORDER_WIDTH}
        worldUnits={false}
        transparent
        depthTest={false}
        depthWrite={false}
        renderOrder={MAP_SCENE.RULER_Y - 1}
      />
      <Line
        points={linePoints}
        color={LINE_COLOR}
        lineWidth={LINE_WIDTH}
        worldUnits={false}
        transparent
        depthTest={false}
        depthWrite={false}
        renderOrder={MAP_SCENE.RULER_Y}
      />
    </>
  );
}
