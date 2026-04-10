import { nanoid } from '@reduxjs/toolkit';

import type { HorizonGraphResponse, UpdateHorizonGraphRequest } from '@/shared/api/endpoints/horizons/types';
import { hasValue } from '@/shared/lib/has-value';

import { fromScene, toScene } from '../../lib/coordinates';

import type { GraphData } from './types';

/**
 * Конвертирует серверный граф ({@link HorizonGraphResponse}) в формат для редактора графа дорог.
 *
 * Алгоритм:
 * 1. Создается маппинг `idToTempId` (серверный `id` → клиентский `tempId`).
 * 2. Обход узлов: каждому узлу генерируется `tempId` (nanoid), пара `id → tempId` записывается в маппинг,
 *    координаты lon/lat конвертируются в `x`/`z` через {@link toScene}.
 * 3. Обход ребер: серверные ссылки `from_node_id`/`to_node_id` конвертируются через маппинг в клиентские `fromId`/`toId`,
 *    каждому ребру присваивается клиентский `tempId` через nanoid, серверный `id` сохраняется.
 *
 * @example
 * ```
 * // Вход (серверный формат):
 * { nodes: [{ id: 1, x: 59.82, y: 58.17 }, { id: 2, x: 59.83, y: 58.18 }],
 *   edges: [{ id: 10, from_node_id: 1, to_node_id: 2 }] }
 *
 * // Выход (формат редактора):
 * { nodes: [{ id: 1, tempId: 'abc1', x: 1.68, z: -1.38 }, { id: 2, tempId: 'abc2', x: 6.68, z: 3.62 }],
 *   edges: [{ id: 10, tempId: 'xyz', fromId: 'abc1', toId: 'abc2' }] }
 * ```
 */
export function serverToEditor(server: HorizonGraphResponse) {
  const idToTempId = new Map<number, string>();

  const nodes = server.nodes.map((node) => {
    const tempId = nanoid();
    idToTempId.set(node.id, tempId);
    const [x, , z] = toScene(node.x, node.y);
    return { id: node.id, tempId, x, z };
  });

  const edges = server.edges.map((edge) => ({
    id: edge.id,
    tempId: nanoid(),
    fromId: idToTempId.get(edge.from_node_id) ?? '',
    toId: idToTempId.get(edge.to_node_id) ?? '',
  }));

  return { nodes, edges };
}

/**
 * Конвертирует граф из формата редактора в серверный формат ({@link UpdateHorizonGraphRequest}).
 *
 * Алгоритм:
 * 1. Создается маппинг `tempIdToServerId` (клиентский `tempId` → серверный `id`
 *    или строковый `tempId` для новых узлов, у которых `id === null`).
 * 2. Обход узлов: пара `tempId → id | tempId` записывается в маппинг, координаты `x`/`z` конвертируются обратно в lon/lat через {@link fromScene}.
 * 3. Обход ребер: клиентские `fromId`/`toId` конвертируются через маппинг в серверные `from_node_id`/`to_node_id`.
 */
export function editorToServer(editor: GraphData): UpdateHorizonGraphRequest {
  const tempIdToServerId = new Map<string, number | string>();

  const nodes = editor.nodes.map((node) => {
    tempIdToServerId.set(node.tempId, node.id ?? node.tempId);
    const { lon, lat } = fromScene(node.x, node.z);
    return { id: node.id ?? node.tempId, x: lon, y: lat };
  });

  const edges = editor.edges.map((edge) => {
    const mapped = {
      from_node_id: tempIdToServerId.get(edge.fromId) ?? edge.fromId,
      to_node_id: tempIdToServerId.get(edge.toId) ?? edge.toId,
    };

    return hasValue(edge.id) ? { id: edge.id, ...mapped } : mapped;
  });

  return { nodes, edges };
}
