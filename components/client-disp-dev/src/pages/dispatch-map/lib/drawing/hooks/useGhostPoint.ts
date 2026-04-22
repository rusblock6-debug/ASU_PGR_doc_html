import { useFrame } from '@react-three/fiber';
import type { RefObject } from 'react';
import { useRef } from 'react';
import type { Object3D } from 'three';

import { projectOnSegment } from '../model/geometry';
import type { GhostPointInfo, ScenePoint, Segment } from '../model/types';

/** Параметры хука {@link useGhostPoint}. */
interface UseGhostPointOptions {
  /** Ref с текущей позицией курсора на плоскости. */
  readonly pointerRef: RefObject<ScenePoint>;
  /** Сегменты, по которым искать проекцию. */
  readonly segments: readonly Segment[];
  /** Точки — ghost-точка не отображается, если курсор над существующей точкой. */
  readonly points: readonly ScenePoint[];
  /** Колбэк, возвращающий true, если сейчас перетаскиваем (ghost-точку скрываем). */
  readonly isDragging: () => boolean;
  /** Y-координата слоя + смещение для позиционирования. */
  readonly y: number;
  /** Дополнительное смещение по Y для ghost-точки. */
  readonly pointYOffset: number;
  /** Размер точки (для зоны «курсор над точкой»). */
  readonly pointSize: number;
  /** Половина ширины зоны захвата сегмента. */
  readonly hitRadius: number;
}

/**
 * Хук для отображения ghost-точки — ближайшей проекции курсора на сегмент.
 */
export function useGhostPoint({
  pointerRef,
  segments,
  points,
  isDragging,
  y,
  pointYOffset,
  pointSize,
  hitRadius,
}: UseGhostPointOptions) {
  const ghostMeshRef = useRef<Object3D>(null);
  const ghostInfoRef = useRef<GhostPointInfo | null>(null);

  useFrame(() => {
    const mesh = ghostMeshRef.current;
    if (!mesh) return;

    const { x, z } = pointerRef.current;
    const ghost = computeGhostPoint({
      cursorPosition: { x, z },
      segments,
      points,
      pointSize,
      isDragging: isDragging(),
      hitRadius,
    });

    ghostInfoRef.current = ghost;

    if (ghost) {
      mesh.position.set(ghost.x, y + pointYOffset, ghost.z);
      mesh.visible = true;
    } else {
      mesh.visible = false;
    }
  });

  return { ghostMeshRef, ghostInfoRef };
}

/** Параметры {@link computeGhostPoint}. */
interface ComputeGhostPointOptions {
  /** Текущая позиция курсора на плоскости (null — нет данных). */
  readonly cursorPosition: ScenePoint | null;
  /** Сегменты, по которым искать ближайшую точку. */
  readonly segments: readonly Segment[];
  /** Координаты точек — ghost-точка не отображается, если курсор над точкой. */
  readonly points: readonly ScenePoint[];
  /** Радиус точки в единицах сцены. */
  readonly pointSize: number;
  /** Если сейчас перетаскиваем (ghost-точку скрываем). */
  readonly isDragging: boolean;
  /** Половина ширины зоны захвата сегмента. По умолчанию 8. */
  readonly hitRadius?: number;
}

/**
 * Вычисляет ghost-точку — ближайшую проекцию курсора на один из сегментов.
 *
 * Возвращает `null`, если курсор далеко от всех сегментов,
 * находится над существующей точкой, или drag активен.
 */
export function computeGhostPoint({
  cursorPosition,
  segments,
  points,
  pointSize,
  isDragging,
  hitRadius = 8,
}: ComputeGhostPointOptions) {
  if (!cursorPosition || segments.length === 0 || isDragging) return null;

  const isOverPoint = points.some((point) => {
    const dx = cursorPosition.x - point.x;
    const dz = cursorPosition.z - point.z;
    return dx * dx + dz * dz < pointSize * pointSize;
  });
  if (isOverPoint) return null;

  let closest: GhostPointInfo | null = null;
  let closestDist = Infinity;

  for (const segment of segments) {
    const projected = projectOnSegment(
      cursorPosition.x,
      cursorPosition.z,
      segment.ax,
      segment.az,
      segment.bx,
      segment.bz,
    );
    const dx = cursorPosition.x - projected.x;
    const dz = cursorPosition.z - projected.z;
    const dist = Math.sqrt(dx * dx + dz * dz);

    if (dist < closestDist && dist < hitRadius) {
      closestDist = dist;
      closest = { x: projected.x, z: projected.z, segmentId: segment.id };
    }
  }

  return closest;
}
