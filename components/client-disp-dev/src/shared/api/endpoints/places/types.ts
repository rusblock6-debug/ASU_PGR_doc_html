import type { Pagination } from '@/shared/api/types';
import type { LocationModel } from '@/shared/models/LocationModel';

/** Представляет тип места. */
export type PlaceType = Place['type'];

/** Представляет модель места. */
export type Place = LoadPlace | UnloadPlace | ReloadPlace | ParkPlace | TransitPlace;

/** Представляет общую модель места. */
export interface BasePlace {
  /** Возвращает идентификатор. */
  readonly id: number;
  /** Возвращает наименование. */
  readonly name: string;
  /** Возвращает идентификатор узла графа. */
  readonly node_id: number | null;
  /** Возвращает идентификатор типа груза. */
  readonly cargo_type: number | null;
  /** Возвращает идентификаторы участков через связь места с horizon и section_horizons. */
  readonly section_ids: readonly number[];
  /** Возвращает локацию. */
  readonly location: LocationModel | null;
  /** Возвращает координату X (Canvas координата или GPS lon, в зависимости от контекста). */
  readonly x: number | null;
  /** Возвращает координату Y (Canvas координата или GPS lat, в зависимости от контекста). */
  readonly y: number | null;
  /** Возвращает идентификатор горизонта. */
  readonly horizon_id: number | null;
  /** Возвращает признак активности. */
  readonly is_active: boolean;
  /** Возвращает время создания. */
  readonly created_at: string;
  /** Возвращает время обновления. */
  readonly updated_at: string;
}

/** Представляет тип для места погрузки. */
export interface LoadPlace extends BasePlace {
  /** Возвращает тип места. */
  readonly type: 'load';
  /** Возвращает дату начала эксплуатации. */
  readonly start_date: string;
  /** Возвращает дату конца эксплуатации. */
  readonly end_date: string | null;
  /** Возвращает текущий остаток. */
  readonly current_stock: number | null;
}

/** Представляет тип для места разгрузки. */
export interface UnloadPlace extends BasePlace {
  /** Возвращает тип места. */
  readonly type: 'unload';
  /** Возвращает дату начала эксплуатации. */
  readonly start_date: string;
  /** Возвращает дату конца эксплуатации. */
  readonly end_date: string | null;
  /** Возвращает вместимость. */
  readonly capacity: number | null;
  /** Возвращает текущий остаток. */
  readonly current_stock: number | null;
}

/** Представляет тип для места перегрузки. */
interface ReloadPlace extends BasePlace {
  /** Возвращает тип места. */
  readonly type: 'reload';
  /** Возвращает дату начала эксплуатации. */
  readonly start_date: string;
  /** Возвращает дату конца эксплуатации. */
  readonly end_date: string | null;
  /** Возвращает вместимость. */
  readonly capacity: number | null;
  /** Возвращает текущий остаток. */
  readonly current_stock: number | null;
}

/** Представляет тип для места стоянки. */
interface ParkPlace extends BasePlace {
  /** Возвращает тип места. */
  readonly type: 'park';
}

/** Представляет тип для транзитного места. */
interface TransitPlace extends BasePlace {
  /** Возвращает тип места. */
  readonly type: 'transit';
}

/** Представляет фильтры мест. */
export interface PlacesQueryArgs {
  /** Возвращает фильтр по типу места. */
  readonly type?: PlaceType;
  /** Возвращает фильтр по типу места. */
  readonly types?: readonly PlaceType[];
  /** Возвращает фильтр по состоянию активности места. */
  readonly is_active?: boolean;
}

/** Представляет модель данных, получаемую по запросу мест. */
export interface PlacesResponse extends Pagination {
  /** Возвращает список мест. */
  readonly items: readonly Place[];
}

/** Представляет модель данных для создания места. */
export interface PlaceCreateRequest {
  /** Возвращает наименование. */
  readonly name: string;
  /** Возвращает тип места. */
  readonly type: PlaceType;
  /** Возвращает идентификатор узла графа. */
  readonly node_id?: number | null;
  /** Возвращает идентификатор вида груза. */
  readonly cargo_type?: number | null;
  /** Возвращает идентификатор для синхронизации с сервером. */
  readonly id?: number | null;
  /** Возвращает дату начала эксплуатации (обязательно для load, unload, reload). */
  readonly start_date?: string | null;
  /** Возвращает дату окончания эксплуатации. */
  readonly end_date?: string | null;
  /** Возвращает вместимость (только для unload, reload). */
  readonly capacity?: number | null;
  /** Возвращает текущий запас. */
  readonly current_stock?: number | null;
}

/** Представляет модель данных для частичного обновления места. */
export interface PlacePatchRequest {
  /** Возвращает наименование. */
  readonly name?: string | null;
  /** Возвращает тип места. */
  readonly type?: PlaceType | null;
  /** Возвращает идентификатор узла графа. */
  readonly node_id?: number | null;
  /** Возвращает идентификатор вида груза. */
  readonly cargo_type?: number | null;
  /** Возвращает источник изменения. */
  readonly source?: string | null;
  /** Возвращает дату начала эксплуатации. */
  readonly start_date?: string | null;
  /** Возвращает дату окончания эксплуатации. */
  readonly end_date?: string | null;
  /** Возвращает вместимость. */
  readonly capacity?: number | null;
  /** Возвращает текущий запас. */
  readonly current_stock?: number | null;
}

/** Представляет модель данных для попапа места на карте. */
export interface PlacePopupResponse {
  /** Возвращает идентификатор вида груза. */
  readonly cargo_type: number | null;
  /** Возвращает текущий остаток. */
  readonly current_stock: number | null;
  /** Возвращает плановое значение груза. */
  readonly planned_value: number | null;
  /** Возвращает фактическое значение груза. */
  readonly real_value: number | null;
  /** Возвращает список id техники в зоне. */
  readonly vehicle_id_list: readonly number[] | null;
}

/** Проверяет, является ли переданное место местом погрузки. Гарантированно сужает тип места, до места погрузки. */
export function isLoadPlace(place?: Place): place is LoadPlace {
  return place?.type === 'load';
}

/** Проверяет, является ли переданное место местом разгрузки. Гарантированно сужает тип места, до места разгрузки. */
export function isUnloadPlace(place?: Place): place is UnloadPlace {
  return place?.type === 'unload';
}
