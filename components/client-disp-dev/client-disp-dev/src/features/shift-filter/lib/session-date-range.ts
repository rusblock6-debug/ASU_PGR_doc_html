import type { DateRangeFilter } from '../model/date-range-filter';

/**
 * Диапазон дат, сериализованный для хранения (ISO 8601).
 */
interface SerializedDateRangeFilter {
  /** Начальная дата. */
  readonly from: string;
  /** Дата окончания. */
  readonly to: string;
}

/**
 * Читает фильтр диапазона дат из `sessionStorage`.
 *
 * Возвращает `null`, если значение отсутствует, JSON невалиден или даты некорректны.
 */
export const getDateRangeFromSession = (key: string) => {
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;

    const parsed = JSON.parse(raw) as SerializedDateRangeFilter;
    const from = new Date(parsed.from);
    const to = new Date(parsed.to);

    if (Number.isNaN(from.getTime()) || Number.isNaN(to.getTime())) return null;

    return { from, to } satisfies DateRangeFilter;
  } catch {
    return null;
  }
};

/**
 * Сохраняет фильтр диапазона дат в `sessionStorage` (ISO 8601).
 */
export const saveDateRangeToSession = (key: string, filter: DateRangeFilter) => {
  sessionStorage.setItem(key, JSON.stringify({ from: filter.from.toISOString(), to: filter.to.toISOString() }));
};
