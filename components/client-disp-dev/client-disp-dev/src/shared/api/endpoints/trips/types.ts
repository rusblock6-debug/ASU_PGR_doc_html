import type { Pagination } from '@/shared/api/types';

/**
 * Источник создания цикла/рейса.
 * - `system` — создан системой автоматически
 * - `dispatcher` — создан диспетчером вручную
 */
export type TripSource = 'system' | 'dispatcher';

/**
 * Тип рейса.
 * - `planned` — плановый рейс
 * - `unplanned` — внеплановый рейс
 */
export type TripType = 'planned' | 'unplanned';

/**
 * Статус рейса.
 * - `active` — активный рейс
 * - `completed` — завершённый рейс
 * - `cancelled` — отменённый рейс
 */
export type TripStatus = 'active' | 'completed' | 'cancelled';

/** Представляет рейс транспортного средства. */
export interface Trip {
  /** ID цикла/рейса (первичный ключ, одинаковый для Cycle и Trip). */
  readonly cycle_id: string;
  /** Порядковый номер рейса в рамках смены. */
  readonly cycle_num: number | null;
  /** ID транспорта. */
  readonly vehicle_id: number;
  /** ID задания. */
  readonly task_id: string | null;
  /** ID смены. */
  readonly shift_id: string | null;
  /** Объем в рейсе. */
  readonly change_amount: number | null;
  /** Время начала цикла (начало движения порожняком). ISO 8601 datetime. */
  readonly cycle_started_at: string | null;
  /** Время завершения цикла (окончание разгрузки). ISO 8601 datetime. */
  readonly cycle_completed_at: string | null;
  /** Источник создания цикла (dispatcher/system). По умолчанию "system". */
  readonly source: TripSource;
  /** Тип рейса (planned/unplanned). */
  readonly trip_type: TripType | null;
  /** Время начала рейса. ISO 8601 datetime. */
  readonly start_time: string | null;
  /** Время окончания рейса. ISO 8601 datetime. */
  readonly end_time: string | null;
  /** Место начала цикла (place.id). */
  readonly from_place_id: number | null;
  /** Место окончания цикла (place.id). */
  readonly to_place_id: number | null;
  /** ID места погрузки (place.id). */
  readonly loading_place_id: number | null;
  /** Название места погрузки. */
  readonly loading_place_name: string | null;
  /** ID места разгрузки (place.id). */
  readonly unloading_place_id: number | null;
  /** Название места разгрузки. */
  readonly unloading_place_name: string | null;
  /** Tag погрузки. */
  readonly loading_tag: string | null;
  /** Tag разгрузки. */
  readonly unloading_tag: string | null;
  /** Время погрузки. ISO 8601 datetime. */
  readonly loading_timestamp: string | null;
  /** Время разгрузки. ISO 8601 datetime. */
  readonly unloading_timestamp: string | null;
  /** Время создания записи. ISO 8601 datetime. */
  readonly created_at: string;
  /** Время обновления записи. ISO 8601 datetime. */
  readonly updated_at: string;
}

/** Расширенная модель рейса с дополнительной информацией о транспорте. */
export interface EnrichedTrip extends Trip {
  /** Название транспортного средства. */
  readonly vehicle_name: string;
}

/** Представляет аргументы запроса списка рейсов. */
export interface TripsQueryArg {
  /** Фильтр по ID транспорта. */
  readonly vehicle_id?: number;
  /** Фильтр по ID задания. */
  readonly task_id?: string;
  /** Фильтр по статусу рейса. */
  readonly status?: TripStatus;
  /** Фильтр по типу рейса. */
  readonly trip_type?: TripType;
  /** Только завершённые рейсы. */
  readonly completed_only?: boolean;
  /** Начало периода (ISO 8601 date). */
  readonly from_date?: string;
  /** Конец периода (ISO 8601 date). */
  readonly to_date?: string;
}

/** Представляет модель данных, получаемую по запросу списка рейсов. */
export interface TripsResponse extends Pagination {
  /** Элементы списка рейсов. */
  readonly items: readonly Trip[];
}

/** Представляет модель данных для создания рейса. */
export interface CreateTripRequest {
  /** ID транспорта. */
  readonly vehicle_id: number;
  /** ID места погрузки (place.id). */
  readonly loading_place_id: number;
  /** ID места разгрузки (place.id). */
  readonly unloading_place_id: number;
  /** Время начала цикла. ISO 8601 datetime. */
  readonly cycle_started_at: string;
  /** Время завершения цикла. ISO 8601 datetime. */
  readonly cycle_completed_at: string;
  /** Время погрузки. ISO 8601 datetime. */
  readonly loading_timestamp?: string | null;
  /** Время разгрузки. ISO 8601 datetime. */
  readonly unloading_timestamp?: string | null;
  /** Вес в рейсе. */
  readonly change_amount?: number | null;
}

/** Представляет модель данных для редактирования рейса. */
export interface UpdateTripRequest {
  /** ID транспорта. */
  readonly vehicle_id?: number;
  /** ID места погрузки (place.id). */
  readonly loading_place_id?: number;
  /** Время погрузки. ISO 8601 datetime. */
  readonly loading_timestamp?: string;
  /** ID места разгрузки (place.id). */
  readonly unloading_place_id?: number;
  /** Время разгрузки. ISO 8601 datetime. */
  readonly unloading_timestamp?: string;
  /** Время начала цикла. ISO 8601 datetime. */
  readonly cycle_started_at?: string;
  /** Время завершения цикла. ISO 8601 datetime. */
  readonly cycle_completed_at?: string;
  /** Вес в рейсе. */
  readonly change_amount: number | null;
}
