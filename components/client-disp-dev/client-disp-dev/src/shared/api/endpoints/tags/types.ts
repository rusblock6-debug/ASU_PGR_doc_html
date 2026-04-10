import type { PlaceType } from '@/shared/api/endpoints/places';
import type { Pagination } from '@/shared/api/types';
import type { LocationModel } from '@/shared/models/LocationModel';

/** Представляет метку. */
export interface Tag {
  /** ID метки. */
  readonly id: number;
  /** Идентификатор метки (beacon_id). */
  readonly tag_name: string | null;
  /** MAC адрес метки в формате XX:XX:XX:XX:XX:XX или XX-XX-XX-XX-XX-XX или XXXXXXXXXXXX. */
  readonly tag_mac: string;
  /** Радиус действия в метрах (beacon_radius). */
  readonly radius: number;
  /** Уровень заряда (beacon_power, 0-100, только для чтения). */
  readonly battery_level: number | null;
  /** Дата изменения уровня заряда. */
  readonly battery_updated_at: string | null;
  /** ID связанного места. */
  readonly place_id: number | null;
  /** Связанное место. */
  readonly place: TagPlace | null;
  /** Canvas координата X из place.location. */
  readonly x: number | null;
  /** Canvas координата Y из place.location. */
  readonly y: number | null;
  /** Высота из place.horizon.height. */
  readonly z: number | null;
  /** ID горизонта из place.horizon_id. */
  readonly horizon_id: number | null;
  /** Название места. */
  readonly name: string | null;
  /** Тип места. */
  readonly point_type: string | null;
  /** tag_name для обратной совместимости. */
  readonly point_id: string | null;
  /** tag_name для обратной совместимости. */
  readonly beacon_id: string | null;
  /** tag_mac для обратной совместимости. */
  readonly beacon_mac: string | null;
  /** Название места. */
  readonly beacon_place: string | null;
}

/** Представляет связанное место для метки. */
export interface TagPlace {
  /** Название места. */
  readonly name: string;
  /** Тип места. */
  readonly type: PlaceType;
  /** Местоположение. */
  readonly location: LocationModel | null;
}

/** Представляет ответ API со списком меток. */
export interface TagsApiResponse extends Pagination {
  readonly items: readonly Tag[];
}

/** Представляет запрос на создание метки. */
export interface CreateTagRequest {
  /** Идентификатор метки (beacon_id). */
  readonly tag_name?: string | null;
  /** MAC адрес метки в формате XX:XX:XX:XX:XX:XX или XX-XX-XX-XX-XX-XX или XXXXXXXXXXXX. */
  readonly tag_mac: string;
  /** Радиус действия в метрах (beacon_radius). */
  readonly radius?: number;
  /** Уровень заряда (beacon_power, только для чтения). */
  readonly battery_level?: number | null;
  /** Дата изменения уровня заряда. */
  readonly battery_updated_at?: string | null;
  /** ID связанного места. */
  readonly place_id?: number | null;
  /** Алиас для tag_name (для обратной совместимости). */
  readonly tag_id?: string | null;
}

/** Представляет параметры обновления метки. */
export interface UpdateTagParams {
  /** ID метки. */
  readonly id: number;
  /** Тело запроса. */
  readonly body: UpdateTagRequest;
}

/** Представляет запрос на обновление метки. */
export interface UpdateTagRequest {
  /** Идентификатор метки (beacon_id). */
  readonly tag_name: string;
  /** MAC адрес метки. */
  readonly tag_mac: string;
  /** Радиус действия в метрах. */
  readonly radius?: number;
  /** Уровень заряда (beacon_power, 0-100). */
  readonly battery_level?: number | null;
  /** Дата изменения уровня заряда. */
  readonly battery_updated_at?: string | null;
  /** ID связанного места. */
  readonly place_id?: number | null;
}
