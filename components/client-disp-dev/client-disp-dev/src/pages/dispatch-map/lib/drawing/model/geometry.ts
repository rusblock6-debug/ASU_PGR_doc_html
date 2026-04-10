import type { GraphEdge, GraphNode } from '../../../model/graph';

import type { PolylinePoint, ScenePoint, Segment } from './types';

/**
 * Строит массив сегментов из последовательных точек полилинии.
 */
export function buildSegments(points: readonly PolylinePoint[]) {
  if (points.length < 2) return [];

  return points.slice(0, -1).map((p, i) => ({
    id: String(i),
    ax: p.x,
    az: p.z,
    bx: points[i + 1].x,
    bz: points[i + 1].z,
  }));
}

/**
 * Строит сегменты из ребер и узлов графа для проверки попадания курсора и ghost-точки.
 */
export function buildEdgeSegments(edges: readonly GraphEdge[], nodesMap: ReadonlyMap<string, GraphNode>) {
  const segments: Segment[] = [];

  for (const edge of edges) {
    const from = nodesMap.get(edge.fromId);
    const to = nodesMap.get(edge.toId);
    if (!from || !to) continue;
    segments.push({ id: edge.tempId, ax: from.x, az: from.z, bx: to.x, bz: to.z });
  }

  return segments;
}

/**
 * Проецирует точку (px, pz) на отрезок AB, возвращая ближайшую точку на отрезке.
 */
export function projectOnSegment(px: number, pz: number, ax: number, az: number, bx: number, bz: number) {
  const abx = bx - ax;
  const abz = bz - az;
  const dot = abx * abx + abz * abz;
  if (dot === 0) return { x: ax, z: az };
  const t = Math.max(0, Math.min(1, ((px - ax) * abx + (pz - az) * abz) / dot));
  return { x: ax + t * abx, z: az + t * abz };
}

/**
 * Проверяет, находится ли точка (cx, cz) в радиусе от хотя бы одной точки из массива.
 */
export function isNearAnyPoint(cx: number, cz: number, points: readonly ScenePoint[], radius: number) {
  const r2 = radius * radius;
  return points.some((p) => {
    const dx = cx - p.x;
    const dz = cz - p.z;
    return dx * dx + dz * dz < r2;
  });
}

/**
 * Проверяет, находится ли точка (cx, cz) в радиусе от хотя бы одного сегмента.
 */
export function isNearAnySegment(cx: number, cz: number, segments: readonly Segment[], radius: number) {
  const r2 = radius * radius;
  return segments.some((s) => {
    const projected = projectOnSegment(cx, cz, s.ax, s.az, s.bx, s.bz);
    const dx = cx - projected.x;
    const dz = cz - projected.z;
    return dx * dx + dz * dz < r2;
  });
}
