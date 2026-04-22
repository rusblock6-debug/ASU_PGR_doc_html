/**
 * Представляет набор методов для управления масштабом таймлайна.
 */
export interface TimelineZoomControl {
  /** Возвращает метод для увеличения масштаба. */
  readonly zoomIn: (amount?: number) => void;
  /** Возвращает метод для уменьшения масштаба. */
  readonly zoomOut: (amount?: number) => void;
  /** Возвращает метод для показа всех элементов таймлайна.  */
  readonly zoomToFit: () => void;
  /** Возвращает метод для показа выбранного диапазона. */
  readonly zoomToRange: (start: Date, end: Date) => void;
  /** Возвращает метод для установки значения масштаба. */
  readonly setZoom: (zoomLevel: number) => void;
  /** Возвращает метод для получения текущего значения масштаба. */
  readonly getCurrentZoom: () => number;
  /** Возвращает метод для перемещения к текущему времени. */
  readonly goToNow: () => void;
  /** Возвращает метод для перемещения к выбранной дате. */
  readonly goToDate: (date: Date) => void;
}
