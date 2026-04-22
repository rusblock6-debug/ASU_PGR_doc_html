/** Представляет модель аналитической категории. */
export interface AnalyticCategory {
  /** Возвращает значение аналитической категории. */
  readonly value: string;
  /** Возвращает отображаемое имя аналитической категории. */
  readonly display_name: string;
}

/** Представляет модель данных, получаемую по запросу аналитических категорий. */
export type AnalyticCategoryResponse = readonly AnalyticCategory[];
