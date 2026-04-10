import type { GraphData, GraphEdge } from './types';

/**
 * Проверяет структурное равенство двух графов (порядок элементов не важен).
 *
 * - Узлы считаются равными, если совпадают `tempId`, `x` и `z`.
 * - Ребра сравниваются как ненаправленные: A → B и B → A — одно и то же ребро.
 */
export function isGraphEqual(a: GraphData, b: GraphData) {
  if (a.nodes.length !== b.nodes.length || a.edges.length !== b.edges.length) return false;

  const sortedA = [...a.nodes].sort((x, y) => x.tempId.localeCompare(y.tempId));
  const sortedB = [...b.nodes].sort((x, y) => x.tempId.localeCompare(y.tempId));

  for (let i = 0; i < sortedA.length; i++) {
    if (sortedA[i].tempId !== sortedB[i].tempId || sortedA[i].x !== sortedB[i].x || sortedA[i].z !== sortedB[i].z) {
      return false;
    }
  }

  const edgeSetA = new Set(a.edges.map(normalizeEdge));
  if (edgeSetA.size !== a.edges.length) return false;

  const edgeSetB = new Set(b.edges.map(normalizeEdge));
  if (edgeSetB.size !== b.edges.length) return false;

  for (const key of edgeSetA) {
    if (!edgeSetB.has(key)) return false;
  }

  return true;
}

/**
 * Сортирует пару id ребра лексикографически, чтобы A → B и B → A давали одинаковый ключ.
 */
function normalizeEdge(edge: GraphEdge) {
  // Разделитель, который не может встретиться внутри nanoid.
  const SAFE_SEPARATOR = '\0';

  const [first, second] = edge.fromId < edge.toId ? [edge.fromId, edge.toId] : [edge.toId, edge.fromId];
  return `${first}${SAFE_SEPARATOR}${second}`;
}
