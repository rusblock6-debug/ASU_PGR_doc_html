import { createSelector } from '@reduxjs/toolkit';

import { EMPTY_ARRAY } from '@/shared/lib/constants';

import { isGraphEqual } from './graph-compare';

/** Узлы редактируемого графа. */
export const selectDraftNodes = (state: RootState) => state.graphEdit.draft?.nodes ?? EMPTY_ARRAY;

/** Ребра редактируемого графа. */
export const selectDraftEdges = (state: RootState) => state.graphEdit.draft?.edges ?? EMPTY_ARRAY;

/** Граф на момент начала редактирования. */
const selectInitialDraft = (state: RootState) => state.graphEdit.initialDraft;

/** Граф, который сейчас редактирует пользователь. `null`, если режим редактирования выключен. */
export const selectDraft = (state: RootState) => state.graphEdit.draft;

/** Узлы редактируемого графа, индексированные по `tempId`. */
export const selectDraftNodesMap = createSelector(
  selectDraftNodes,
  (nodes) => new Map(nodes.map((node) => [node.tempId, node])),
);

/** Есть ли несохраненные изменения в графе. */
export const selectIsGraphDirty = createSelector(selectInitialDraft, selectDraft, (initial, draft) => {
  if (!initial || !draft) return false;
  return !isGraphEqual(initial, draft);
});

/** Превью цвета дороги (до сохранения). */
export const selectPreviewColor = (state: RootState) => state.graphEdit.previewColor;
