import { createSelector } from '@reduxjs/toolkit';

import type { TreeNodeValue } from './types';

/** Проверяет, раскрыт ли раздел сайдбара. */
export const selectIsTreeNodeExpanded = createSelector(
  [(state: RootState) => state.map.expandedTreeNodes, (_state: RootState, key: TreeNodeValue) => key],
  (nodes, key) => nodes.includes(key),
);

/** Режим работы карты. */
export const selectMapMode = (state: RootState) => state.map.mode;

/** Идентификатор скрытой техники. */
export const selectHiddenVehicleIds = (state: RootState) => state.map.hiddenVehicleIds;

/** Идентификатор скрытых мест. */
export const selectHiddenPlaceIds = (state: RootState) => state.map.hiddenPlaceIds;

/** Видимость слоёв. */
export const selectMapLayers = (state: RootState) => state.map.layers;

/** Объект для фокусировки камеры. */
export const selectMapFocusTarget = (state: RootState) => state.map.focusTarget;

/** Сортировка по группам техники. */
export const selectVehicleGroupSorts = (state: RootState) => state.map.vehicleGroupSorts;

/** Сортировка по группам мест. */
export const selectPlaceGroupSorts = (state: RootState) => state.map.placeGroupSorts;

/** Фильтр отображения объектов по горизонту («На горизонте»/«Все»). */
export const selectHorizonFilter = (state: RootState) => state.map.horizonFilter;

/** Создаваемый или редактируемый объект. */
export const selectFormTarget = (state: RootState) => state.map.formTarget;

/** Наличие несохраненных изменений. */
export const selectHasUnsavedChanges = (state: RootState) => state.map.hasUnsavedChanges;

/** Активен ли режим редактирования дорожного графа. */
export const selectIsGraphEditActive = (state: RootState) => state.map.isGraphEditActive;

/** Активна ли линейка. */
export const selectIsRulerActive = (state: RootState) => state.map.isRulerActive;

/** Место для размещения на карте. */
export const selectPlacementPlaceToAdd = (state: RootState) => state.map.placementPlaceToAdd;

/** Сортировка подложек. */
export const selectBackgroundSort = (state: RootState) => state.map.backgroundSort;

/** Предпросмотр яркости подложки (0–100), null — предпросмотра нет. */
export const selectBackgroundPreviewOpacity = (state: RootState) => state.map.backgroundPreviewOpacity;

/** Идентификатор выбранного горизонта. */
export const selectSelectedHorizonId = (state: RootState) => state.map.selectedHorizonId;

/** Данные контекстного меню для транспорта. */
export const selectVehicleContextMenu = (state: RootState) => state.map.vehicleContextMenu;

/** Диапазон показа истории. */
export const selectHistoryRangeFilter = (state: RootState) => state.map.historyRangeFilter;

/** Идентификаторы выбранных элементов для показа истории. */
export const selectSelectedVehicleHistoryIds = (state: RootState) => state.map.selectedVehicleHistoryIds;

/** Признак видимости плеера истории. */
export const selectIsVisibleHistoryPlayer = (state: RootState) => state.map.isVisibleHistoryPlayer;

/** Признак запущенного плеера истории. */
export const selectIsPlayHistoryPlayer = (state: RootState) => state.map.isPlayHistoryPlayer;

/** Текущее время плеера истории. */
export const selectPlayerCurrentTime = (state: RootState) => state.map.playerCurrentTime;

/** Состояние загрузки. */
export const selectIsLoading = (state: RootState) => state.map.isLoading;

/** Процент загрузки. */
export const selectLoadPercentage = (state: RootState) => state.map.loadPercentage;

/** Список сохраненных следов в истории перемещения оборудования. */
export const selectVehicleHistoryMarks = (state: RootState) => state.map.vehicleHistoryMarks;
