/** Ответ GET /api/event-log/current-shift-stats */
export interface CurrentShiftStatsResponse {
  /** Дата смены (как возвращает API). */
  readonly shift_date: string;
  /** Номер смены. */
  readonly shift_num: number;
  /** Суммарное время работы (в секундах/как возвращает API). */
  readonly work_time_sum: number;
  /** Суммарное время простоя. */
  readonly idle_time_sum: number;
  /** Фактическое количество рейсов/поездок (суммарно). */
  readonly actual_trips_count_sum: number;
  /** Плановое количество рейсов/поездок (суммарно). */
  readonly planned_trips_count_sum: number;
  /** Фактический суммарный объём (м³). */
  readonly actual_volume_sum: number;
  /** Плановый суммарный объём (м³). */
  readonly planned_volume_sum: number;
  /** Фактический суммарный вес (т). */
  readonly actual_weight_sum: number;
  /** Плановый суммарный вес (т). */
  readonly planned_weight_sum: number;
}
