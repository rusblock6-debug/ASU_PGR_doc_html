import type { PlaceType } from '@/shared/api/endpoints/places';

/**
 * Типы мест с названия для использования в метках.
 * Каждый ключ это тип места из PlaceType, значение — его название.
 */
export const placeTypeLabels = {
  load: 'Погрузочная',
  unload: 'Разгрузочная',
  transit: 'Транзитная',
  reload: 'Перегрузочная',
  park: 'Транспортная',
} as const satisfies Record<PlaceType, string>;
