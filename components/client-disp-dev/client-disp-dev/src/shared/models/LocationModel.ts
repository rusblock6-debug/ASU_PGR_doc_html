/**
 * Представляет модель локации.
 */
export interface LocationModel {
  /**
   * Возвращает координату широты.
   */
  readonly lat: number;
  /**
   * Возвращает координату долготы.
   */
  readonly lon: number;
}

/**
 * Пустые координаты на случай отсутствия валидной локации.
 * Используется `null` вместо `undefined`, так как React Hook Form не сбрасывает значение поля при `undefined`.
 */
export const EMPTY_COORDINATES = { lat: null, lon: null } as const;

/**
 * Нормализует локацию: возвращает валидную {@link LocationModel} или пустые координаты.
 * Проверяет что оба поля (lat и lon) являются числами.
 *
 * @param location Частичная или полная локация, может быть null/undefined.
 * @returns Валидная {@link LocationModel} если оба поля — числа, иначе пустые координаты.
 */
export function normalizeLocation(location?: Partial<LocationModel> | null) {
  if (location && typeof location.lat === 'number' && typeof location.lon === 'number') {
    return location as LocationModel;
  }
  return EMPTY_COORDINATES;
}
