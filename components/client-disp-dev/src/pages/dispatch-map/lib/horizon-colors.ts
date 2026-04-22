import type { Horizon } from '@/shared/api/endpoints/horizons';
import { hasValue } from '@/shared/lib/has-value';

import { GraphElementType } from '../model/graph';
import type { GraphEdge, GraphNode } from '../model/graph';

/**
 * Параметры вычисления цвета лестничного узла.
 */
interface GetLadderNodeColorParams {
  /** Узел графа, для которого вычисляется цвет. */
  readonly node: GraphNode;
  /** Идентификатор текущего выбранного горизонта. */
  readonly currentHorizonId: number;
  /** Список доступных горизонтов с их цветами. */
  readonly horizons?: readonly Horizon[];
  /** Цвет по умолчанию, если подходящий горизонт не найден. */
  readonly fallbackColor: string;
}

/**
 * Параметры вычисления цвета лестничного ребра.
 */
interface GetLadderEdgeColorParams {
  /** Ребро графа, для которого вычисляется цвет. */
  readonly edge: GraphEdge;
  /** Карта вершин графа по идентификатору. */
  readonly nodesMap: ReadonlyMap<string, GraphNode>;
  /** Идентификатор текущего выбранного горизонта. */
  readonly currentHorizonId: number;
  /** Список доступных горизонтов с их цветами. */
  readonly horizons?: readonly Horizon[];
  /** Цвет по умолчанию, если подходящий горизонт не найден. */
  readonly fallbackColor: string;
}

/**
 * Вычисляет цвет лестничного узла по `horizonId` связанного горизонта.
 */
export function getLadderNodeColor({ node, currentHorizonId, horizons, fallbackColor }: GetLadderNodeColorParams) {
  if (node.nodeType !== GraphElementType.LADDER || !hasValue(node.horizonId) || node.horizonId === currentHorizonId) {
    return fallbackColor;
  }

  return horizons?.find((horizon) => horizon.id === node.horizonId)?.color ?? fallbackColor;
}

/**
 * Вычисляет цвет лестничного ребра по `horizonId` его вершины.
 */
export function getLadderEdgeColor({
  edge,
  nodesMap,
  currentHorizonId,
  horizons,
  fallbackColor,
}: GetLadderEdgeColorParams) {
  const from = nodesMap.get(edge.fromId);
  const to = nodesMap.get(edge.toId);

  const foreignId = findForeignHorizonId(currentHorizonId, from, to);

  return horizons?.find((horizon) => horizon.id === foreignId)?.color ?? fallbackColor;
}

/**
 * Находит `horizonId` вершины, принадлежащего другому горизонту.
 */
function findForeignHorizonId(currentHorizonId: number, from?: GraphNode, to?: GraphNode) {
  if (hasValue(from?.horizonId) && from.horizonId !== currentHorizonId) {
    return from.horizonId;
  }

  if (hasValue(to?.horizonId) && to.horizonId !== currentHorizonId) {
    return to.horizonId;
  }

  return null;
}
