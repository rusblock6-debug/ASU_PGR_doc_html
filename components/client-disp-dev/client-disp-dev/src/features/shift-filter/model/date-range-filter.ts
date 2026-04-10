/** Представляет фильтр по диапазону дат. */
export interface DateRangeFilter {
  /** Возвращает дату начальной границу. */
  readonly from: Date;
  /** Возвращает дату конечной границу. */
  readonly to: Date;
}
