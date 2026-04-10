import type { Vector3Tuple } from 'three';

import type { PlaceType } from '@/shared/api/endpoints/places';
import type { VehicleType } from '@/shared/api/endpoints/vehicles';
import type { SortState } from '@/shared/lib/sort-by-field';

/** Ключи разделов дерева сайдбара. */
export const TreeNode = {
  OBJECTS: 'objects',
  EQUIPMENT: 'equipment',
  MOBILE_EQUIPMENT: 'mobile_equipment',
  VEHICLES_PDM: 'vehicles_pdm',
  VEHICLES_SHAS: 'vehicles_shas',
  PLACES: 'places',
  PLACES_RELOAD: 'places_reload',
  PLACES_LOAD: 'places_load',
  PLACES_UNLOAD: 'places_unload',
  PLACES_PARK: 'places_park',
  PLACES_TRANSIT: 'places_transit',
  LAYERS: 'layers',
  ROADS: 'roads',
  BACKGROUND_LAYERS: 'background_layers',
} as const;

/** Типы ключей раздела дерева. */
export type TreeNodeValue = (typeof TreeNode)[keyof typeof TreeNode];

/** Режим работы. */
export const Mode = {
  VIEW: 'view',
  EDIT: 'edit',
  HISTORY: 'history',
} as const;

/** Типы значений режима работы. */
export type ModeValue = (typeof Mode)[keyof typeof Mode];

/** Фильтр отображения объектов: на текущем горизонте или все. */
export const HorizonFilter = {
  CURRENT_HORIZON: 'horizon',
  ALL: 'all',
} as const;

/** Значение фильтра отображения объектов по горизонту. */
export type HorizonFilterValue = (typeof HorizonFilter)[keyof typeof HorizonFilter];

/** Слои карты. */
export const MapLayer = {
  ROADS: 'roads',
  BACKGROUND: 'background',
} as const;

/** Типы значений слоя карты. */
export type MapLayerValue = (typeof MapLayer)[keyof typeof MapLayer];

/** Поля сортировки списка подложек. */
export type BackgroundSortField = 'name' | 'horizon';

/** Состояние для страницы «Карта». */
export interface MapState {
  /** Активный режим работы карты. */
  readonly mode: ModeValue;
  /** Фильтр объектов: на горизонте или все. */
  readonly horizonFilter: HorizonFilterValue;
  /** ID скрытой техники. */
  readonly hiddenVehicleIds: readonly number[];
  /** ID скрытых мест. */
  readonly hiddenPlaceIds: readonly number[];
  /** Видимость слоёв карты. */
  readonly layers: Record<MapLayerValue, boolean>;
  /** Объект для фокусировки камеры (null — нет фокуса). */
  readonly focusTarget: FocusTarget | null;
  /** Раскрытые узлы дерева сайдбара. */
  readonly expandedTreeNodes: readonly TreeNodeValue[];
  /** Сортировка по группам техники. */
  readonly vehicleGroupSorts: VehicleGroupSorts;
  /** Сортировка по группам мест. */
  readonly placeGroupSorts: PlaceGroupSorts;
  /** Объект для создания или редактирования. */
  readonly formTarget: FromTarget | null;
  /** Наличие несохраненных изменений. */
  readonly hasUnsavedChanges: boolean;
  /** Место для размещения на карте. */
  readonly placementPlaceToAdd: PlacementPlace | null;
  /** Сортировка списка подложек. */
  readonly backgroundSort: SortState<BackgroundSortField>;
  /** Предпросмотр яркости подложки (0–100), null — предпросмотра нет. */
  readonly backgroundPreviewOpacity: number | null;
  /** Активен ли режим редактирования дорожного графа. */
  readonly isGraphEditActive: boolean;
  /** Активна ли линейка. */
  readonly isRulerActive: boolean;
  /** Идентификатор выбранного горизонта (null — ещё не выбран). */
  readonly selectedHorizonId: number | null;
}

/** Типы целей для фокусировки камеры. */
export interface FocusTarget {
  /** Возвращает тип сущности. */
  readonly entity: 'vehicle' | 'place';
  /** Возвращает идентификатор. */
  readonly id: number;
}

/** Ключ группы техники (без служебного 'vehicle'). */
export type VehicleGroupKey = Exclude<VehicleType, 'vehicle'>;

/** Допустимые поля сортировки. */
export type ObjectListSortField = 'name' | 'stock' | 'horizon';

/** Параметры сортировки по группам техники. */
export type VehicleGroupSorts = Record<VehicleGroupKey, SortState<ObjectListSortField>>;

/** Параметры сортировки по группам мест. */
export type PlaceGroupSorts = Record<PlaceType, SortState<ObjectListSortField>>;

/** Объект для создания или редактирования. */
export interface FromTarget {
  /** Возвращает тип сущности. */
  readonly entity: 'vehicle' | 'place';
  /** Возвращает идентификатор. */
  readonly id: number | null;
}

/** Представляет модель размещаемого места на карте. */
export interface PlacementPlace {
  /** Возвращает тип места. */
  readonly placeType: PlaceType;
  /** Возвращает местоположение. */
  readonly position: Vector3Tuple | null;
  /** Возвращает признак, что место находиться в режиме размещения на карте. */
  readonly isPlacementMode: boolean;
  /** Возвращает серверный идентификатор вершины графа, к которой привязано место. */
  readonly nodeId: number | null;
}
