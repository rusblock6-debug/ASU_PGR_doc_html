import type { Place } from '@/shared/api/endpoints/places';

/**
 * Возвращает опции для селектора мест.
 *
 * @param places список мест.
 */
export function getPlacesOptionsToSelect(places?: readonly Place[]) {
  if (!places) return { load: [], unload: [] };

  return {
    load: places
      .filter((item) => item.type === 'load' || item.type === 'reload')
      .map((item) => ({ value: item.id.toString(), label: item.name })),
    unload: places
      .filter((item) => item.type === 'unload' || item.type === 'reload')
      .map((item) => ({ value: item.id.toString(), label: item.name })),
  };
}
