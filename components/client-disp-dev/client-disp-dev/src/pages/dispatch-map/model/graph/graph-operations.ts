import { EMPTY_ARRAY } from '@/shared/lib/constants';

import type { GraphEdge } from './types';

/**
 * Проверяет, соединены ли два узла ребром (в любом направлении).
 */
export function areConnected(edges: readonly GraphEdge[], nodeIdA: string, nodeIdB: string) {
  return edges.some(
    (edge) => (edge.fromId === nodeIdA && edge.toId === nodeIdB) || (edge.fromId === nodeIdB && edge.toId === nodeIdA),
  );
}

/**
 * Если соседи удалённого узла оказались в разных компонентах связности,
 * возвращает пары узлов, ребра между которыми восстановят связность графа.
 */
export function getReconnectPairs(edges: readonly GraphEdge[], neighborIds: readonly string[]) {
  if (neighborIds.length < 2) return [];

  const adjacency = buildAdjacency(edges);
  const visited = new Set<string>();
  const representatives: string[] = [];

  for (const neighborId of neighborIds) {
    if (visited.has(neighborId)) continue;
    representatives.push(neighborId);
    collectReachable(adjacency, neighborId, visited);
  }

  if (representatives.length < 2) return [];

  return representatives.slice(1).map((toId, i) => [representatives[i], toId]);
}

/**
 * Для каждого узла возвращает массив соседей, с которыми он соединён ребром.
 */
function buildAdjacency(edges: readonly GraphEdge[]) {
  const adjacency = new Map<string, string[]>();

  for (const edge of edges) {
    let fromList = adjacency.get(edge.fromId);
    if (!fromList) {
      fromList = [];
      adjacency.set(edge.fromId, fromList);
    }
    fromList.push(edge.toId);

    let toList = adjacency.get(edge.toId);
    if (!toList) {
      toList = [];
      adjacency.set(edge.toId, toList);
    }
    toList.push(edge.fromId);
  }

  return adjacency;
}

/**
 * Рекурсивный обход в глубину (Depth-first search): начиная с `node`, обходит все достижимые узлы по ребрам
 * и помечает их в `visited`. Позволяет понять, какие узлы связаны друг с другом.
 *
 * @see https://habr.com/ru/articles/504374/ — обход графа: DFS и BFS
 */
function collectReachable(adjacency: ReadonlyMap<string, readonly string[]>, node: string, visited: Set<string>) {
  if (visited.has(node)) return;
  visited.add(node);

  for (const neighbor of adjacency.get(node) ?? EMPTY_ARRAY) {
    collectReachable(adjacency, neighbor, visited);
  }
}
