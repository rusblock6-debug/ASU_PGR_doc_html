import { nanoid } from '@reduxjs/toolkit';

import { graphEditActions } from './graph-edit-slice';
import { getReconnectPairs } from './graph-operations';

/**
 * Удаляет узел из графа и автоматически восстанавливает связность:
 * если после удаления соседи узла теряют путь друг к другу,
 * между ними создаются новые ребра, чтобы граф остался связным.
 */
export const removeNode = (nodeId: string) => {
  return (dispatch: AppDispatch, getState: () => RootState) => {
    const draft = getState().graphEdit.draft;
    if (!draft) return;

    const neighborIds = [
      ...new Set(
        draft.edges
          .filter((edge) => edge.fromId === nodeId || edge.toId === nodeId)
          .map((edge) => (edge.fromId === nodeId ? edge.toId : edge.fromId)),
      ),
    ];
    const remainingEdges = draft.edges.filter((edge) => edge.fromId !== nodeId && edge.toId !== nodeId);
    const reconnectPairs = getReconnectPairs(remainingEdges, neighborIds);
    const reconnectEdges = reconnectPairs.map(([fromId, toId]) => ({ id: null, tempId: nanoid(), fromId, toId }));

    dispatch(graphEditActions._removeNode({ nodeId, reconnectEdges }));
  };
};

/**
 * Разбивает ребро на два, вставляя между его концами новый узел
 * в позиции `(x, z)`. Исходное ребро заменяется двумя новыми:
 * `from → newNode` и `newNode → to`.
 *
 * @returns временный id созданного узла (пустая строка, если ребро не найдено).
 */
export const splitEdge = (edgeId: string, x: number, z: number) => {
  return (dispatch: AppDispatch, getState: () => RootState) => {
    const draft = getState().graphEdit.draft;
    if (!draft) return '';

    const edge = draft.edges.find((edge) => edge.tempId === edgeId);
    if (!edge) return '';

    const tempId = nanoid();
    dispatch(
      graphEditActions._splitEdge({
        edgeId,
        x,
        z,
        tempId,
        edgeAId: nanoid(),
        edgeBId: nanoid(),
      }),
    );

    return tempId;
  };
};
