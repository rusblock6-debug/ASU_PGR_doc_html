import type { ThreeEvent } from '@react-three/fiber';

import { useGroundPointerContext } from '../../ui/GroundPointerProvider';
import { buildSegments, isNearAnyPoint, isNearAnySegment, useClickGuard, usePolylineDrawing } from '../drawing';

/** Радиус зоны вокруг вершины, в которой клик по плоскости игнорируется. */
const POINT_HIT_RADIUS = 5;

/** Максимальное расстояние до сегмента, при котором клик считается попаданием в него. */
const SEGMENT_HIT_RADIUS = 8;

/**
 * Хук для управления состоянием и логикой линейки.
 */
export function useRuler() {
  const { pointerRef } = useGroundPointerContext();

  const { handlePointerDown, isClick } = useClickGuard();

  const { points, addPoint, insertPoint, movePoint, removePoint } = usePolylineDrawing();
  const segments = buildSegments(points);

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    if (!isClick(event)) return;

    const { x, z } = pointerRef.current;
    if (isNearAnyPoint(x, z, points, POINT_HIT_RADIUS)) return;
    if (isNearAnySegment(x, z, segments, SEGMENT_HIT_RADIUS)) return;

    addPoint(x, z);
  };

  return {
    points,
    segments,

    handlePointerDown,
    handleClick,

    insertPoint,
    movePoint,
    removePoint,
  };
}
