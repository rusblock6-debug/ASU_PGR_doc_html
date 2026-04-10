import type { Pagination, PaginationFilter } from '@/shared/api/types';

/** Представляет модель смены в режиме работы предприятия. */
export interface ShiftDefinition {
  /** Возвращает номер смены. */
  readonly shift_num: number;
  /** Возвращает время начала смены в секундах от 00:00 (может быть отрицательным для смен, начинающихся в предыдущий день). */
  readonly start_time_offset: number;
  /** Возвращает время окончания смены в секундах от 00:00. */
  readonly end_time_offset: number;
}

/** Представляет модель режима работы предприятия. */
export interface WorkRegime {
  /** Возвращает идентификатор. */
  readonly id: number;
  /** Возвращает идентификатор предприятия. */
  readonly enterprise_id: number;
  /** Возвращает наименование режима работы. */
  readonly name: string;
  /** Возвращает описание режима работы. */
  readonly description: string | null;
  /** Возвращает список смен в режиме работы. */
  readonly shifts_definition: readonly ShiftDefinition[];
  /** Возвращает признак активности режима. */
  readonly is_active: string;
  /** Возвращает время создания. */
  readonly created_at: string;
  /** Возвращает время обновления. */
  readonly updated_at: string;
}

/** Представляет модель данных, получаемую по запросу режимов работы. */
export interface WorkRegimeResponse extends Pagination {
  /** Возвращает список режимов. */
  readonly items: readonly WorkRegime[];
}

/** Представляет аргументы запроса списка режимов работы предприятия. */
export interface WorkRegimeQueryArg extends PaginationFilter {
  /** Возвращает идентификатор предприятия. */
  readonly enterprise_id: number;
  /** Возвращает признак активности режима. */
  readonly is_active: boolean;
}
