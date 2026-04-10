import type { SortState } from '@/shared/lib/sort-by-field';

import type { BackgroundSortField, PlaceGroupSorts, TreeNodeValue, VehicleGroupSorts } from '../types';
import { TreeNode } from '../types';

import type { PersistFieldConfig, PersistSyncConfig } from './types';

const DEFAULT_EXPANDED = [
  TreeNode.OBJECTS,
  TreeNode.EQUIPMENT,
  TreeNode.MOBILE_EQUIPMENT,
  TreeNode.VEHICLES_PDM,
  TreeNode.VEHICLES_SHAS,
  TreeNode.PLACES,
  TreeNode.LAYERS,
] as const satisfies readonly TreeNodeValue[];

const DEFAULT_SORT = { field: 'name', order: 'asc' } as const satisfies SortState;

const DEFAULT_VEHICLE_GROUP_SORTS = {
  pdm: DEFAULT_SORT,
  shas: DEFAULT_SORT,
} as const satisfies VehicleGroupSorts;

const DEFAULT_PLACE_GROUP_SORTS = {
  reload: DEFAULT_SORT,
  load: DEFAULT_SORT,
  unload: DEFAULT_SORT,
  park: DEFAULT_SORT,
  transit: DEFAULT_SORT,
} as const satisfies PlaceGroupSorts;

export const expandedTreeNodesConfig = {
  key: 'asu-gtk-map-tree-expanded',
  selector: (state) => state.expandedTreeNodes,
  defaultValue: DEFAULT_EXPANDED,
} as const satisfies PersistFieldConfig<readonly TreeNodeValue[]>;

export const vehicleGroupSortsConfig = {
  key: 'asu-gtk-map-vehicle-sorts',
  selector: (state) => state.vehicleGroupSorts,
  defaultValue: DEFAULT_VEHICLE_GROUP_SORTS,
} as const satisfies PersistFieldConfig<VehicleGroupSorts>;

export const placeGroupSortsConfig = {
  key: 'asu-gtk-map-place-sorts',
  selector: (state) => state.placeGroupSorts,
  defaultValue: DEFAULT_PLACE_GROUP_SORTS,
} as const satisfies PersistFieldConfig<PlaceGroupSorts>;

export const backgroundSortConfig = {
  key: 'asu-gtk-map-background-sort',
  selector: (state) => state.backgroundSort,
  defaultValue: DEFAULT_SORT,
} as const satisfies PersistFieldConfig<SortState<BackgroundSortField>>;

export const selectedHorizonIdConfig = {
  key: 'asu-gtk-map-selected-horizon',
  selector: (state) => state.selectedHorizonId,
  defaultValue: null,
} as const satisfies PersistFieldConfig<number | null>;

/**
 * Все персистентные поля слайса карты.
 * Чтобы добавить сохранение в LocalStorage новому полю — создайте здесь конфиг и добавьте его сюда.
 */
export const MAP_PERSIST_CONFIGS: readonly PersistSyncConfig[] = [
  expandedTreeNodesConfig,
  vehicleGroupSortsConfig,
  placeGroupSortsConfig,
  backgroundSortConfig,
  selectedHorizonIdConfig,
];
