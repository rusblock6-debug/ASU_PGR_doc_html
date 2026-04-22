import type { PayloadAction } from '@reduxjs/toolkit';
import { createSlice } from '@reduxjs/toolkit';

import type { MapPlayerPlaybackItem } from '@/shared/api/endpoints/map-player';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { toggleSort } from '@/shared/lib/sort-by-field';

import { toggleBatch } from './lib/toggle-batch';
import {
  backgroundSortConfig,
  expandedTreeNodesConfig,
  horizonFilterConfig,
  loadPersistedField,
  modeConfig,
  placeGroupSortsConfig,
  selectedHorizonIdConfig,
  vehicleGroupSortsConfig,
} from './persist';
import type {
  BackgroundSortField,
  FocusTarget,
  FromTarget,
  HorizonFilterValue,
  MapLayerValue,
  MapState,
  ModeValue,
  ObjectListSortField,
  PlaceGroupSorts,
  TreeNodeValue,
  VehicleContextMenuState,
  VehicleGroupSorts,
  PlacementPlace,
  HistoryRangeFilter,
} from './types';
import { MapLayer } from './types';

const initialLayers: Record<MapLayerValue, boolean> = {
  [MapLayer.ROADS]: true,
  [MapLayer.BACKGROUND]: true,
};

const initialState: MapState = {
  mode: loadPersistedField(modeConfig),
  horizonFilter: loadPersistedField(horizonFilterConfig),
  hiddenVehicleIds: EMPTY_ARRAY,
  hiddenPlaceIds: EMPTY_ARRAY,
  layers: initialLayers,
  focusTarget: null,
  expandedTreeNodes: loadPersistedField(expandedTreeNodesConfig),
  vehicleGroupSorts: loadPersistedField(vehicleGroupSortsConfig),
  placeGroupSorts: loadPersistedField(placeGroupSortsConfig),
  backgroundSort: loadPersistedField(backgroundSortConfig),
  formTarget: null,
  hasUnsavedChanges: false,
  placementPlaceToAdd: null,
  backgroundPreviewOpacity: null,
  isGraphEditActive: false,
  isRulerActive: false,
  selectedHorizonId: loadPersistedField(selectedHorizonIdConfig),
  vehicleContextMenu: null,
  historyRangeFilter: null,
  selectedVehicleHistoryIds: EMPTY_ARRAY,
  isVisibleHistoryPlayer: false,
  isPlayHistoryPlayer: false,
  playerCurrentTime: null,
  isLoading: false,
  loadPercentage: null,
  vehicleHistoryMarks: EMPTY_ARRAY,
};

export const slice = createSlice({
  name: 'map',
  initialState,
  reducers: {
    /**
     * Установить режим работы карты.
     */
    setMode(state, action: PayloadAction<ModeValue>) {
      state.mode = action.payload;
    },

    /**
     * Установить фильтр объектов (на горизонте / все).
     */
    setObjectFilter(state, action: PayloadAction<HorizonFilterValue>) {
      state.horizonFilter = action.payload;
    },

    /**
     * Переключить видимость техники.
     */
    toggleVehicleVisibility(state, action: PayloadAction<number>) {
      const id = action.payload;
      const idx = state.hiddenVehicleIds.indexOf(id);
      if (idx === -1) {
        state.hiddenVehicleIds.push(id);
      } else {
        state.hiddenVehicleIds.splice(idx, 1);
      }
    },

    /**
     * Переключить видимость места.
     */
    togglePlaceVisibility(state, action: PayloadAction<number>) {
      const id = action.payload;
      const idx = state.hiddenPlaceIds.indexOf(id);
      if (idx === -1) {
        state.hiddenPlaceIds.push(id);
      } else {
        state.hiddenPlaceIds.splice(idx, 1);
      }
    },

    /**
     * Переключить видимость группы техники.
     */
    toggleVehiclesVisibility(state, action: PayloadAction<readonly number[]>) {
      state.hiddenVehicleIds = toggleBatch(state.hiddenVehicleIds, action.payload);
    },

    /**
     * Переключить видимость группы мест.
     */
    togglePlacesVisibility(state, action: PayloadAction<readonly number[]>) {
      state.hiddenPlaceIds = toggleBatch(state.hiddenPlaceIds, action.payload);
    },

    /**
     * Переключить видимость слоя.
     */
    toggleLayerVisibility(state, action: PayloadAction<MapLayerValue>) {
      state.layers[action.payload] = !state.layers[action.payload];
    },

    /**
     * Установить объект для фокусировки камеры. `null` — сбросить фокус.
     */
    setFocusTarget(state, action: PayloadAction<FocusTarget | null>) {
      state.focusTarget = action.payload;
    },

    /**
     * Переключить сортировку для группы техники или мест.
     */
    toggleGroupSort(
      state,
      action: PayloadAction<
        | { entity: 'vehicle'; group: keyof VehicleGroupSorts; field: ObjectListSortField }
        | { entity: 'place'; group: keyof PlaceGroupSorts; field: ObjectListSortField }
        | { entity: 'background'; field: BackgroundSortField }
      >,
    ) {
      const { payload } = action;
      if (payload.entity === 'vehicle') {
        state.vehicleGroupSorts[payload.group] = toggleSort(state.vehicleGroupSorts[payload.group], payload.field);
      } else if (payload.entity === 'place') {
        state.placeGroupSorts[payload.group] = toggleSort(state.placeGroupSorts[payload.group], payload.field);
      } else {
        state.backgroundSort = toggleSort(state.backgroundSort, payload.field);
      }
    },

    /**
     * Установить предпросмотр яркости подложки (0–100). null — сбросить предпросмотр.
     */
    setBackgroundPreviewOpacity(state, action: PayloadAction<number | null>) {
      state.backgroundPreviewOpacity = action.payload;
    },

    /**
     * Раскрыть или свернуть раздел сайдбара.
     */
    toggleTreeNode(state, action: PayloadAction<TreeNodeValue>) {
      const key = action.payload;
      const idx = state.expandedTreeNodes.indexOf(key);
      if (idx === -1) {
        state.expandedTreeNodes.push(key);
      } else {
        state.expandedTreeNodes.splice(idx, 1);
      }
    },

    /**
     * Выбрать объект для создания или редактирования.
     */
    setFormTarget(state, action: PayloadAction<FromTarget | null>) {
      state.formTarget = action.payload;
    },

    /**
     * Изменить состояние наличия изменений.
     */
    setHasUnsavedChanges(state, action: PayloadAction<boolean>) {
      state.hasUnsavedChanges = action.payload;
    },

    /**
     * Изменить состояние места размещаемого на карте.
     */
    setPlacementPlaceToAdd(state, action: PayloadAction<PlacementPlace | null>) {
      state.placementPlaceToAdd = action.payload;
    },

    /**
     * Переключить режим редактирования дорожного графа.
     */
    toggleGraphEdit(state) {
      state.isGraphEditActive = !state.isGraphEditActive;
    },

    /**
     * Переключить линейку.
     */
    toggleRuler(state) {
      state.isRulerActive = !state.isRulerActive;
    },

    /**
     * Установить выбранный горизонт.
     */
    setSelectedHorizonId(state, action: PayloadAction<number | null>) {
      state.selectedHorizonId = action.payload;
    },

    /**
     * Установить состояние контекстного меню транспорта. `null` — скрыть меню.
     */
    setVehicleContextMenu(state, action: PayloadAction<VehicleContextMenuState | null>) {
      state.vehicleContextMenu = action.payload;
    },

    /**
     * Установить значение диапазона показа истории.
     */
    setHistoryRangeFilter(state, action: PayloadAction<HistoryRangeFilter | null>) {
      state.historyRangeFilter = action.payload;
    },

    /**
     * Переключить элемент для показа истории.
     */
    toggleVehicleHistoryId(state, action: PayloadAction<number>) {
      const id = action.payload;
      const idx = state.selectedVehicleHistoryIds.indexOf(id);
      if (idx === -1) {
        state.selectedVehicleHistoryIds.push(id);
      } else {
        state.selectedVehicleHistoryIds.splice(idx, 1);
      }
    },

    /**
     * Переключить группу элементов для показа истории.
     */
    toggleVehicleHistoryIds(state, action: PayloadAction<readonly number[]>) {
      const selectedIds = state.selectedVehicleHistoryIds;
      const selectedSet = new Set(selectedIds);
      const payloadSet = new Set(action.payload);

      const allSelected = action.payload.every((id) => selectedSet.has(id));

      if (allSelected) {
        state.selectedVehicleHistoryIds = selectedIds.filter((id) => !payloadSet.has(id));
      } else {
        state.selectedVehicleHistoryIds = Array.from(new Set([...selectedIds, ...action.payload]));
      }
    },

    /**
     * Переключить видимость плеера истории.
     */
    toggleVisibleHistoryPlayer(state, action: PayloadAction<boolean>) {
      state.isVisibleHistoryPlayer = action.payload;
    },

    /**
     * Запустить/остановить плеер истории.
     */
    togglePlayHistoryPlayer(state, action: PayloadAction<boolean>) {
      state.isPlayHistoryPlayer = action.payload;
    },

    /**
     * Установить значение текущего времени плеера истории.
     */
    setPlayerCurrentTime(state, action: PayloadAction<number | null>) {
      state.playerCurrentTime = action.payload;
    },

    /**
     * Переключить состояние загрузки.
     */
    toggleLoading(state, action: PayloadAction<boolean>) {
      state.isLoading = action.payload;
    },

    /**
     * Установить значение процента загрузки.
     */
    setLoadPercentage(state, action: PayloadAction<number | null>) {
      state.loadPercentage = action.payload;
    },

    /**
     * Изменить список сохраненных следов в истории перемещения оборудования.
     */
    setVehicleHistoryMarks(state, action: PayloadAction<readonly MapPlayerPlaybackItem[]>) {
      state.vehicleHistoryMarks = [...action.payload];
    },
  },
});

export const mapActions = slice.actions;
export const mapReducer = slice.reducer;
