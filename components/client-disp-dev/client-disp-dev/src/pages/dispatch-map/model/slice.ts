import type { PayloadAction } from '@reduxjs/toolkit';
import { createSlice } from '@reduxjs/toolkit';

import { toggleSort } from '@/shared/lib/sort-by-field';

import { toggleBatch } from './lib/toggle-batch';
import {
  backgroundSortConfig,
  expandedTreeNodesConfig,
  loadPersistedField,
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
  VehicleGroupSorts,
  PlacementPlace,
} from './types';
import { HorizonFilter, MapLayer, Mode } from './types';

const initialLayers: Record<MapLayerValue, boolean> = {
  [MapLayer.ROADS]: true,
  [MapLayer.BACKGROUND]: true,
};

const initialState: MapState = {
  mode: Mode.VIEW,
  horizonFilter: HorizonFilter.ALL,
  hiddenVehicleIds: [],
  hiddenPlaceIds: [],
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
     * Установить объект для фокусировки камеры.
     */
    setFocusTarget(state, action: PayloadAction<FocusTarget>) {
      state.focusTarget = action.payload;
    },

    /**
     * Сбросить фокус камеры.
     */
    clearFocusTarget(state) {
      state.focusTarget = null;
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
  },
});

export const mapActions = slice.actions;
export const mapReducer = slice.reducer;
