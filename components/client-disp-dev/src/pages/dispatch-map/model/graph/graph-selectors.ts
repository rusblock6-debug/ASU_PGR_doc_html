import { createSelector } from '@reduxjs/toolkit';

import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';

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

/** Цвет дороги горизонта на момент начала редактирования. */
export const selectRoadColor = (state: RootState) => state.graphEdit.roadColor;

/** Есть ли несохранённое изменение цвета дороги. */
export const selectIsColorDirty = (state: RootState) => state.graphEdit.previewColor !== null;

/** Активен ли режим редактирования переездов. */
export const selectIsLadderEditActive = (state: RootState) => state.graphEdit.isLadderEditActive;

/** Вершина-источник переезда. */
export const selectLadderSource = (state: RootState) => state.graphEdit.ladderSource;

/** Целевая вершина переезда. */
export const selectLadderTarget = (state: RootState) => state.graphEdit.ladderTarget;

/** Есть ли несохраненные изменения в переезде (лестнице). */
export const selectIsLadderDirty = createSelector(
  [selectLadderSource, selectLadderTarget],
  (source, target) => hasValue(source) || hasValue(target),
);

/** Можно ли сохранить переезд (выбраны обе вершины). */
export const selectCanSaveLadder = createSelector(
  [selectLadderSource, selectLadderTarget],
  (source, target) => hasValue(source) && hasValue(target),
);
