import type { DataItem } from 'vis-timeline/standalone';

/**
 * Представляет расширенный тип элемента таймлана.
 */
export type TimelineItemExtended = DataItem & {
  /** Возвращает идентификатор предыдущего элемента. */
  readonly prevItemId?: string;
  /** Возвращает идентификатор следующего элемента. */
  readonly nextItemId?: string;
  /** Возвращает системное имя статуса. */
  readonly systemName?: string;
  /** Возвращает признак того, что статус является системным. */
  readonly isSystemStatus?: boolean;
  /** Возвращает идентификатор цикла. */
  readonly cycleId?: string | null;
};
