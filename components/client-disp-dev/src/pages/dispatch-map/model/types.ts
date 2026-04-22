import type { Vector3Tuple } from 'three';

import type { MapPlayerPlaybackItem } from '@/shared/api/endpoints/map-player';
import type { PlaceType } from '@/shared/api/endpoints/places';
import type { VehicleType } from '@/shared/api/endpoints/vehicles';
import type { SortState } from '@/shared/lib/sort-by-field';
import type { ElementCoordinates } from '@/shared/ui/types';

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
  LADDERS: 'ladders',
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

/** Данные контекстного меню транспорта на карте. */
export interface VehicleContextMenuState {
  /** Идентификатор транспортного средства. */
  readonly vehicleId: number;
  /** Экранные координаты точки правого клика. */
  readonly clickPosition: ElementCoordinates;
}

/** Модель диапазона показа истории оборудования. */
export interface HistoryRangeFilter {
  /** Начальная дата. */
  readonly from: string;
  /** Конечная дата. */
  readonly to: string;
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

/** Состояние для страницы «Карта». */
export interface MapState {
  /** Активный режим работы карты. */
  readonly mode: ModeValue;
  /** Фильтр объектов: на горизонте или все. */
  readonly horizonFilter: HorizonFilterValue;
  /** Идентификатор скрытой техники. */
  readonly hiddenVehicleIds: readonly number[];
  /** Идентификатор скрытых мест. */
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
  /** Предпросмотр яркости подложки (0–100), null — предварительного просмотра нет. */
  readonly backgroundPreviewOpacity: number | null;
  /** Активен ли режим редактирования дорожного графа. */
  readonly isGraphEditActive: boolean;
  /** Активна ли линейка. */
  readonly isRulerActive: boolean;
  /** Идентификатор выбранного горизонта (null — ещё не выбран). */
  readonly selectedHorizonId: number | null;
  /** Контекстное меню транспорта (null — скрыто). */
  readonly vehicleContextMenu: VehicleContextMenuState | null;
  /** Фильтр по диапазону для показа истории. */
  readonly historyRangeFilter: HistoryRangeFilter | null;
  /** Список идентификаторов, выбранного для показа истории, оборудования. */
  readonly selectedVehicleHistoryIds: readonly number[];
  /** Видимость плеера показа истории. */
  readonly isVisibleHistoryPlayer: boolean;
  /** Состояние работы плеера истории. */
  readonly isPlayHistoryPlayer: boolean;
  /** Текущее время плеера истории. */
  readonly playerCurrentTime: number | null;
  /** Состояние загрузки. */
  readonly isLoading: boolean;
  /** Процент загрузки. */
  readonly loadPercentage: number | null;
  /** Список следов оборудования в истории. */
  readonly vehicleHistoryMarks: readonly MapPlayerPlaybackItem[];
}
