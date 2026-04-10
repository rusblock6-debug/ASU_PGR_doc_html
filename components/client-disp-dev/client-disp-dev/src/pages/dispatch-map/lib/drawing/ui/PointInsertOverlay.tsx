import type { ThreeEvent } from '@react-three/fiber';
import type { RefObject } from 'react';

import { hasValue } from '@/shared/lib/has-value';

import { MAP_SCENE } from '../../../config/map-scene';
import { useCoordinatedDrag } from '../hooks/useCoordinatedDrag';
import { useGhostPoint } from '../hooks/useGhostPoint';
import { HORIZONTAL_ROTATION } from '../model/constants';
import { isNearAnyPoint, projectOnSegment } from '../model/geometry';
import type { MoveScenePoint, ScenePoint, Segment } from '../model/types';

/** Ширина невидимой области для клика по сегменту. */
const SEGMENT_HIT_WIDTH = 16;
/** Прозрачность ghost-точки. */
const GHOST_POINT_OPACITY = 0.5;
/** Смещение области для клика по сегменту по Y над плоскостью линейки. */
const SEGMENT_Y_OFFSET = 0.01;

/**
 * Представляет свойства компонента {@link PointInsertOverlay}.
 */
interface PointInsertOverlayProps {
  /** Точки, по которым определяется, что курсор «над точкой». */
  readonly points: readonly ScenePoint[];
  /** Сегменты, над которыми размещаются невидимые плоскости для нажатия. */
  readonly segments: readonly Segment[];
  /** Вставляет новую точку на сегменте. Возвращает ID новой сущности. */
  readonly onInsert: (segmentId: string, x: number, z: number) => string;
  /** Перемещает точку по плоскости. */
  readonly onMove: MoveScenePoint;
  /** Y-координата слоя. */
  readonly y: number;
  /** Цвет ghost-точки. */
  readonly ghostColor: string;
  /** Размер точки в px. */
  readonly pointSize: number;
  /** Толщина обводки ghost-точки. Если не задана — обводка не отображается. */
  readonly ghostBorderWidth?: number;
  /** Цвет обводки ghost-точки. */
  readonly ghostBorderColor?: string;
  /** Радиус зоны захвата сегмента для ghost-точки. */
  readonly hitRadius: number;
  /** Ref с текущей позицией курсора на плоскости. */
  readonly pointerRef: RefObject<ScenePoint>;
  /** При `true` — dragPositionRef обновляется каждый кадр, `onMove` вызывается только при отпускании. */
  readonly deferMove?: boolean;
}

/**
 * Слой вставки новых точек на линии.
 *
 * Над каждым сегментом размещается невидимая плоскость, реагирующая на клик.
 * При наведении на сегмент появляется полупрозрачная ghost-точка,
 * показывающая место будущей вставки. Клик по сегменту или по ghost-точке создаёт новую вершину.
 */
export function PointInsertOverlay({
  points,
  segments,
  onInsert,
  onMove,
  y,
  ghostColor,
  pointSize,
  ghostBorderWidth,
  ghostBorderColor,
  hitRadius,
  pointerRef,
  deferMove,
}: PointInsertOverlayProps) {
  const { startDrag, isDragging } = useCoordinatedDrag({ y, onMove, deferMove });

  const { ghostMeshRef, ghostInfoRef } = useGhostPoint({
    pointerRef,
    segments,
    points,
    isDragging,
    y,
    pointYOffset: MAP_SCENE.POINT_ABOVE_LAYER_Y,
    pointSize,
    hitRadius,
  });

  const handleSegmentPointerDown = (segmentId: string, event: ThreeEvent<PointerEvent>) => {
    if (event.button !== 0) return;
    if (isNearAnyPoint(event.point.x, event.point.z, points, pointSize)) return;

    event.stopPropagation();

    const segment = segments.find((segment) => segment.id === segmentId);
    if (!segment) return;

    const projected = projectOnSegment(event.point.x, event.point.z, segment.ax, segment.az, segment.bx, segment.bz);
    const newId = onInsert(segmentId, projected.x, projected.z);
    startDrag(newId);
  };

  const handleGhostPointerDown = (event: ThreeEvent<PointerEvent>) => {
    if (event.button !== 0) return;

    const ghost = ghostInfoRef.current;
    if (!ghost) return;

    event.stopPropagation();
    const newId = onInsert(ghost.segmentId, ghost.x, ghost.z);
    startDrag(newId);
  };

  return (
    <>
      {segments.map((segment) => {
        const dx = segment.bx - segment.ax;
        const dz = segment.bz - segment.az;
        const length = Math.sqrt(dx * dx + dz * dz);
        if (length === 0) return null;

        const angle = Math.atan2(dx, dz);

        return (
          <mesh
            key={segment.id}
            position={[(segment.ax + segment.bx) / 2, y + SEGMENT_Y_OFFSET, (segment.az + segment.bz) / 2]}
            rotation={[-Math.PI / 2, -angle, 0]}
            onPointerDown={(event) => handleSegmentPointerDown(segment.id, event)}
            onClick={(event) => event.stopPropagation()}
            renderOrder={y}
          >
            <planeGeometry args={[SEGMENT_HIT_WIDTH, length]} />
            <meshBasicMaterial
              transparent
              opacity={0}
              depthWrite={false}
            />
          </mesh>
        );
      })}

      <group
        ref={ghostMeshRef}
        visible={false}
        rotation={HORIZONTAL_ROTATION}
        onPointerDown={handleGhostPointerDown}
      >
        {hasValue(ghostBorderWidth) && (
          <mesh renderOrder={y + 1}>
            <circleGeometry args={[pointSize + ghostBorderWidth, 24]} />
            <meshBasicMaterial
              color={ghostBorderColor}
              transparent
              opacity={GHOST_POINT_OPACITY}
              depthTest={false}
              depthWrite={false}
            />
          </mesh>
        )}
        <mesh
          position={hasValue(ghostBorderWidth) ? [0, 0, 0.001] : undefined}
          renderOrder={y + 2}
        >
          <circleGeometry args={[pointSize, 24]} />
          <meshBasicMaterial
            color={ghostColor}
            transparent
            opacity={GHOST_POINT_OPACITY}
            depthTest={false}
          />
        </mesh>
      </group>
    </>
  );
}
